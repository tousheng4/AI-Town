# 多人游戏管理器
extends Node

# 网络配置
const DEFAULT_PORT = 7777
const MAX_PLAYERS = 4

# 玩家角色场景 (需要在编辑器中设置)
var player_scene: PackedScene = null

# 玩家出生点
var spawn_points: Array[Vector2] = [
	Vector2(200, 200),
	Vector2(300, 200),
	Vector2(400, 200),
	Vector2(500, 200)
]

# 多人模式类型
enum MultiplayerMode {
	DISABLED,	# 禁用 (单人模式)
	HOST,		# 主机 (创建房间)
	CLIENT		# 客户端 (加入房间)
}

var current_mode: MultiplayerMode = MultiplayerMode.DISABLED
var peer: ENetMultiplayerPeer = ENetMultiplayerPeer.new()

# 玩家数据
var players_info: Dictionary = {}  # {peer_id: {name: "xxx", r: float, g: float, b: float}}

# 本地玩家名称 (客户端使用)
var local_player_name: String = "Player"

# 信号
signal player_connected(peer_id: int)
signal player_disconnected(peer_id: int)
signal connection_failed()
signal game_started()
signal spawn_player(peer_id: int, player_info: Dictionary)
signal despawn_player(peer_id: int)

func _ready():
	# 尝试加载玩家场景
	player_scene = preload("res://scenes/player.tscn")

	# 配置多人系统信号
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connection_failed.connect(_on_connection_failed)

	print("[INFO] 多人游戏管理器初始化完成")

# ========== 主机功能 ==========

func create_game(player_name: String = "Host") -> bool:
	"""创建游戏房间 (作为主机)"""
	print("[INFO] 正在创建游戏房间...")

	# 创建服务器
	var error = peer.create_server(DEFAULT_PORT, MAX_PLAYERS)
	if error != OK:
		print("[ERROR] 创建服务器失败: ", error)
		return false

	# 设置多人peer
	multiplayer.multiplayer_peer = peer

	current_mode = MultiplayerMode.HOST

	# 添加主机玩家信息
	var peer_id = multiplayer.get_unique_id()
	if peer_id == 0:
		peer_id = 1  # 主机默认ID为1

	# 简单数据类型
	players_info[peer_id] = {
		"name": player_name,
		"r": randf(),
		"g": randf(),
		"b": randf(),
		"is_host": true
	}

	# 设置当前玩家信息（用于API请求区分多玩家）
	Config.player_id = player_name
	Config.player_name = player_name

	# 注意: 不在这里生成主机玩家!
	# 主机玩家已经在场景中 (_ready时创建)，main.gd会在game_started时处理
	# 只需要通知客户端 (但还没有客户端，所以这一步可以跳过)

	game_started.emit()
	print("[INFO] 游戏房间创建成功! 等待玩家加入...")
	return true

# ========== 客户端功能 ==========

func join_game(ip_address: String, player_name: String = "Player") -> bool:
	"""加入游戏房间 (作为客户端)"""
	print("[INFO] 正在连接到: ", ip_address)

	# 创建客户端
	var error = peer.create_client(ip_address, DEFAULT_PORT)
	if error != OK:
		print("[ERROR] 连接服务器失败: ", error)
		return false

	# 设置多人peer
	multiplayer.multiplayer_peer = peer

	current_mode = MultiplayerMode.CLIENT

	# 保存本地玩家名称
	local_player_name = player_name

	# 设置当前玩家信息（用于API请求区分多玩家）
	Config.player_id = player_name
	Config.player_name = player_name

	print("[INFO] 正在连接...")
	return true

# ========== 断开连接 ==========

func disconnect_game():
	"""断开连接"""
	if peer:
		peer.close()
		peer = ENetMultiplayerPeer.new()
		multiplayer.multiplayer_peer = null

	players_info.clear()
	current_mode = MultiplayerMode.DISABLED
	print("[INFO] 已断开连接")

# ========== 玩家生成 ==========

func spawn_player_for_peer(peer_id: int, player_info):
	"""为指定peer生成玩家角色"""

	# 验证参数
	if typeof(player_info) != TYPE_DICTIONARY:
		print("[ERROR] player_info 不是字典类型!")
		return

	if not player_scene:
		print("[ERROR] 玩家场景未设置!")
		return

	# 获取场景根节点
	var game_root = get_tree().current_scene
	if not game_root:
		print("[ERROR] 无法获取游戏场景根节点, current_scene=", get_tree().current_scene)
		# 尝试获取根节点
		game_root = get_tree().root
		if not game_root:
			print("[ERROR] 无法获取根节点")
			return

	# 确保 player_info 是有效的字典
	if not (typeof(player_info) == TYPE_DICTIONARY and player_info.size() > 0):
		print("[ERROR] player_info 无效: ", player_info)
		return

	# 找到或创建Players节点
	var players_node = game_root.get_node_or_null("Players")
	if not players_node:
		players_node = Node2D.new()
		players_node.name = "Players"
		game_root.add_child(players_node)

	# 检查是否已存在该玩家
	var my_peer_id = get_my_peer_id()
	if players_node.has_node("Player_" + str(peer_id)):
		# 如果是自己（peer_id == my_peer_id），不需要更新 authority
		# 这是本地玩家，authority 已经在 main.gd 中正确设置
		if peer_id == my_peer_id:
			return

		# 如果是其他玩家，更新 authority（这是远程玩家）
		var existing_player = players_node.get_node("Player_" + str(peer_id))
		existing_player.set_multiplayer_authority(peer_id)
		existing_player.peer_id = peer_id
		existing_player.is_multiplayer = true
		return

	# 实例化玩家
	var player = player_scene.instantiate()
	player.name = "Player_" + str(peer_id)
	player.set_multiplayer_authority(peer_id)  # 设置网络 authority

	# 安全地获取玩家信息
	player.player_name = "Player"
	player.player_color = Color.WHITE

	if "name" in player_info:
		player.player_name = str(player_info["name"])

	# 处理颜色 (简单格式: r, g, b)
	if "r" in player_info and "g" in player_info and "b" in player_info:
		var r = float(player_info["r"])
		var g = float(player_info["g"])
		var b = float(player_info["b"])
		player.player_color = Color(r, g, b)

	player.peer_id = peer_id

	# 设置出生位置 (安全访问，增加边界检查)
	var spawn_index = 0
	var safe_size = min(players_info.size(), spawn_points.size())
	if safe_size > 0:
		spawn_index = (safe_size - 1) % spawn_points.size()
	# 再次确保索引有效
	spawn_index = clamp(spawn_index, 0, spawn_points.size() - 1)
	if spawn_points.size() > spawn_index:
		player.position = spawn_points[spawn_index]
	else:
		player.position = Vector2(0, 200)  # 默认位置

	# 添加到场景
	players_node.add_child(player)

	# 确保玩家可见
	player.visible = true

	# 打印当前所有玩家
	for child in players_node.get_children():
		print("  - ", child.name, " visible=", child.visible, " pos=", child.position)

	# 调试: 打印场景结构

	print("[INFO] 为玩家 ", peer_id, " 生成角色: ", player_info.get("name", "Player"))
	spawn_player.emit(peer_id, player_info)

func despawn_player_for_peer(peer_id: int):
	"""移除指定peer的玩家角色"""
	var game_root = get_tree().current_scene
	if not game_root:
		return

	var players_node = game_root.get_node_or_null("Players")
	if not players_node:
		return

	var player = players_node.get_node_or_null("Player_" + str(peer_id))
	if player:
		player.queue_free()
		print("[INFO] 移除玩家角色: ", peer_id)
		despawn_player.emit(peer_id)

# ========== 多人同步 ==========

func get_players_info() -> Dictionary:
	"""获取所有玩家信息"""
	return players_info.duplicate()

func get_player_name(peer_id: int) -> String:
	"""获取玩家名称"""
	if players_info.has(peer_id):
		return players_info[peer_id].get("name", "Unknown")
	return "Unknown"

func is_host() -> bool:
	"""是否为主机"""
	return current_mode == MultiplayerMode.HOST

func get_my_peer_id() -> int:
	"""获取自己的peer ID"""
	var id = multiplayer.get_unique_id()
	if id == 0:
		id = 1
	return id

# ========== 内部方法 ==========

func _on_peer_connected(peer_id: int):
	"""有玩家连接"""
	print("[INFO] 玩家连接: ", peer_id)
	player_connected.emit(peer_id)

	# 主机处理新玩家
	if is_host():
		# 发送当前玩家列表给新玩家
		rpc_id(peer_id, "sync_players_list", players_info)

		# 为新玩家生成角色 (如果有的话)
		if players_info.has(peer_id):
			spawn_player_for_peer(peer_id, players_info[peer_id])

		# 注意: 新客户端会通过 rpc_register_player 发送自己的信息

func _on_peer_disconnected(peer_id: int):
	"""有玩家断开"""
	print("[INFO] 玩家断开: ", peer_id)

	# 移除玩家角色
	despawn_player_for_peer(peer_id)

	# 从玩家列表中移除
	if players_info.has(peer_id):
		players_info.erase(peer_id)

	# 通知其他玩家
	if is_host():
		notify_player_left(peer_id)

	player_disconnected.emit(peer_id)

func _on_connection_failed():
	"""连接失败"""
	print("[ERROR] 连接失败!")
	connection_failed.emit()
	current_mode = MultiplayerMode.DISABLED

# ========== RPC 方法 (远程过程调用) ==========

# 同步玩家列表给新连接的玩家
@rpc("reliable")
func sync_players_list(players: Dictionary):
	print("[INFO] 收到玩家列表同步: ", players)

	# 确保 players 是字典类型
	if typeof(players) != TYPE_DICTIONARY:
		print("[ERROR] sync_players_list: players 不是字典类型!")
		return

	# 清除旧数据并重建
	players_info.clear()
	for key in players.keys():
		var peer_id = int(key)
		var player_data = players[key]
		if typeof(player_data) == TYPE_DICTIONARY:
			players_info[peer_id] = player_data  # 直接复制


	# 为所有现有玩家生成角色 (除了自己)
	await get_tree().create_timer(0.1).timeout

	var my_id = get_my_peer_id()

	for pid in players_info.keys():
		if pid != my_id:
			spawn_player_for_peer(pid, players_info[pid])

	# 客户端: 连接成功后向服务器注册自己的信息
	if current_mode == MultiplayerMode.CLIENT:
		var my_info = {
			"name": local_player_name,
			"r": randf(),
			"g": randf(),
			"b": randf(),
			"is_host": false
		}
		rpc_id(1, "register_player", my_id, my_info)

	game_started.emit()

# 通知新玩家加入
@rpc("reliable")
func notify_new_player(new_peer_id: int, player_data):
	print("[INFO] 新玩家加入: ", new_peer_id, " - ", player_data)

	# 确保 player_data 是字典
	if typeof(player_data) == TYPE_DICTIONARY:
		players_info[new_peer_id] = player_data
		# 生成新玩家的角色
		spawn_player_for_peer(new_peer_id, player_data)
	else:
		print("[ERROR] notify_new_player: player_data 不是字典!")
	player_connected.emit(new_peer_id)

# 注册新玩家 (客户端调用)
@rpc("reliable", "any_peer")
func register_player(peer_id: int, player_data):
	"""服务器端: 接收客户端的玩家注册信息"""
	print("[INFO] 收到玩家注册: peer_id=", peer_id, " data=", player_data)

	if typeof(player_data) == TYPE_DICTIONARY:
		players_info[peer_id] = player_data

		# 为新玩家生成角色
		spawn_player_for_peer(peer_id, player_data)

		# 通知其他客户端有新玩家 (排除自己)
		var server_id = multiplayer.get_unique_id()
		for existing_peer in players_info.keys():
			if existing_peer != peer_id and existing_peer != server_id:
				rpc_id(existing_peer, "notify_new_player", peer_id, player_data)

# 通知玩家离开
@rpc("reliable")
func notify_player_left(left_peer_id: int):
	print("[INFO] 玩家离开: ", left_peer_id)

	# 移除玩家角色
	despawn_player_for_peer(left_peer_id)

	if players_info.has(left_peer_id):
		players_info.erase(left_peer_id)
	player_disconnected.emit(left_peer_id)

# 接收玩家位置广播并转发给其他玩家
# 使用 authority 来允许任何人调用 (然后在服务器端转发)
@rpc("reliable", "any_peer")
func broadcast_player_position(source_peer_id: int, position: Vector2, anim_name: String, flip_h: bool):
	"""接收玩家位置并转发给其他客户端"""

	var server_id = multiplayer.get_unique_id()

	# 服务器端：直接调用本地函数来处理位置
	# 这样主机可以看到其他玩家的位置
	if is_host():
		receive_player_position(source_peer_id, position, anim_name, flip_h)

	# 转发给其他客户端 (排除源玩家和服务器自己)
	for pid in players_info.keys():
		if pid != source_peer_id and pid != server_id:
			rpc_id(pid, "receive_player_position", source_peer_id, position, anim_name, flip_h)

# 主机直接广播给其他玩家 (不使用 RPC)
func broadcast_to_others(source_peer_id: int, position: Vector2, anim_name: String, flip_h: bool):
	"""主机直接转发给其他客户端"""
	if not is_host():
		return

	var server_id = multiplayer.get_unique_id()

	# 转发给所有其他玩家 (只排除源玩家自己)
	for pid in players_info.keys():
		if pid != source_peer_id:
			rpc_id(pid, "receive_player_position", source_peer_id, position, anim_name, flip_h)

# 接收转发的玩家位置
@rpc("reliable")
func receive_player_position(source_peer_id: int, position: Vector2, anim_name: String, flip_h: bool):
	"""接收远程玩家的位置更新"""

	# 如果是发给自己的位置，跳过（本地玩家有自己的位置，不需要同步）
	var my_id = get_my_peer_id()
	if source_peer_id == my_id:
		return

	var game_root = get_tree().current_scene
	if not game_root:
		print("[WARN] receive_player_position: no game_root")
		return

	var players_node = game_root.get_node_or_null("Players")
	if not players_node:
		print("[WARN] receive_player_position: no Players node")
		return

	var player = players_node.get_node_or_null("Player_" + str(source_peer_id))
	if not player:
		print("[WARN] receive_player_position: no Player_", source_peer_id)
		# 打印所有玩家
		print("  现有玩家:")
		for child in players_node.get_children():
			print("    - ", child.name)
		return

	if player.has_method("sync_position"):
		player.sync_position(position, anim_name, flip_h)

# ========== 调试辅助函数 ==========

func _get_scene_structure(node: Node, indent: int = 0) -> String:
	"""获取场景结构的调试字符串"""
	if not node:
		return "null"

	var result = ""
	for i in range(indent):
		result += "  "

	result += node.name

	if node is CanvasItem and "visible" in node:
		result += " [visible=" + str(node.visible) + "]"

	result += "\n"

	# 递归子节点
	for child in node.get_children():
		if child is Node:
			result += _get_scene_structure(child, indent + 1)

	return result
