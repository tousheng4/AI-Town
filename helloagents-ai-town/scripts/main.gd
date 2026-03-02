# 主场景脚本
extends Node2D

# NPC节点引用
@onready var npc_zhang: Node2D = $NPCs/NPC_Zhang
@onready var npc_li: Node2D = $NPCs/NPC_Li
@onready var npc_wang: Node2D = $NPCs/NPC_Wang

# 玩家节点引用
@onready var local_player: Node2D = $Player

# API客户端
var api_client: Node = null

# NPC状态更新计时器
var status_update_timer: float = 0.0

# 多人游戏管理器
var multiplayer_manager = null

func _ready():
	print("[INFO] 主场景初始化")

	# 获取API客户端
	api_client = get_node_or_null("/root/APIClient")
	if api_client:
		api_client.npc_status_received.connect(_on_npc_status_received)

		# 立即获取一次NPC状态
		api_client.get_npc_status()
	else:
		print("[ERROR] API客户端未找到")

	# 获取多人管理器
	multiplayer_manager = get_node_or_null("/root/MultiplayerManager")
	if multiplayer_manager:
		# 连接信号
		multiplayer_manager.game_started.connect(_on_multiplayer_game_started)
		multiplayer_manager.spawn_player.connect(_on_spawn_player)
		multiplayer_manager.despawn_player.connect(_on_despawn_player)
		print("[INFO] 多人管理器已连接")
	else:
		print("[WARN] 多人管理器未找到")

func _process(delta: float):
	# 定时更新NPC状态
	status_update_timer += delta
	if status_update_timer >= Config.NPC_STATUS_UPDATE_INTERVAL:
		status_update_timer = 0.0
		if api_client:
			api_client.get_npc_status()

func _on_npc_status_received(dialogues: Dictionary):
	"""收到NPC状态更新"""
	print("[INFO] 更新NPC状态: ", dialogues)

	# 更新各个NPC的对话
	for npc_name in dialogues:
		var dialogue = dialogues[npc_name]
		update_npc_dialogue(npc_name, dialogue)

func update_npc_dialogue(npc_name: String, dialogue: String):
	"""更新指定NPC的对话"""
	var npc_node = get_npc_node(npc_name)
	if npc_node and npc_node.has_method("update_dialogue"):
		npc_node.update_dialogue(dialogue)

func get_npc_node(npc_name: String) -> Node2D:
	"""根据名字获取NPC节点"""
	match npc_name:
		"张三":
			return npc_zhang
		"李四":
			return npc_li
		"王五":
			return npc_wang
		_:
			return null

# ========== 多人游戏相关 ==========

func _on_multiplayer_game_started():
	"""多人游戏开始"""
	print("[INFO] 多人游戏开始!")

	# 获取自己的 peer ID
	var my_id = 1
	if multiplayer_manager:
		my_id = multiplayer_manager.get_my_peer_id()

	# 如果是多人游戏，保留本地玩家
	if multiplayer_manager:
		if local_player:
			local_player.set_multiplayer_authority(my_id)
			local_player.peer_id = my_id
			local_player.is_multiplayer = true
			local_player.visible = true
			local_player.process_mode = Node.PROCESS_MODE_INHERIT

			# 重命名本地玩家，避免与远程玩家冲突
			local_player.name = "Player_" + str(my_id)

			# 移动到 Players 节点下
			var game_root = get_tree().current_scene
			var players_node = game_root.get_node_or_null("Players")
			if not players_node:
				players_node = Node2D.new()
				players_node.name = "Players"
				game_root.add_child(players_node)

			# 从当前父节点移动到 Players
			local_player.get_parent().remove_child(local_player)
			players_node.add_child(local_player)

			print("[INFO] 多人模式: 保留本地玩家 my_id=", my_id, " name=", local_player.name, " parent=", local_player.get_parent().name)

func _on_spawn_player(peer_id: int, player_info: Dictionary):
	"""有玩家加入 (包括自己)"""
	print("[INFO] 收到 spawn_player 信号: ", peer_id, " - ", player_info)

	# 如果是自己，不需要处理 (已经在上面处理过了)
	if multiplayer_manager:
		var my_id = multiplayer_manager.get_my_peer_id()
		if peer_id == my_id:
			return

func _on_despawn_player(peer_id: int):
	"""有玩家离开"""
	print("[INFO] 收到 despawn_player 信号: ", peer_id)
