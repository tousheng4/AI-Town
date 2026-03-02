# 多人游戏菜单 UI
extends Control

# 节点引用
@onready var multiplayer_manager = $"../../MultiplayerManager"
@onready var player_name_input: LineEdit = $Panel/VBoxContainer/PlayerNameInput
@onready var ip_input: LineEdit = $Panel/VBoxContainer/IPInput
@onready var status_label: Label = $Panel/VBoxContainer/StatusLabel

func _ready():
	# 注意: 按钮信号已在场景编辑器中连接，不需要重复连接

	# 连接多人管理器信号
	if multiplayer_manager:
		multiplayer_manager.player_connected.connect(_on_player_connected)
		multiplayer_manager.player_disconnected.connect(_on_player_disconnected)
		multiplayer_manager.connection_failed.connect(_on_connection_failed)
		multiplayer_manager.game_started.connect(_on_game_started)

	# 设置默认值
	if player_name_input:
		player_name_input.text = "Player" + str(randi() % 100)
	if ip_input:
		ip_input.text = "127.0.0.1"

func _on_create_btn_pressed():
	if not multiplayer_manager:
		status_label.text = "错误: 多人管理器未找到!"
		return

	var player_name = player_name_input.text
	if player_name.is_empty():
		player_name = "Host"

	status_label.text = "正在创建房间..."
	var success = multiplayer_manager.create_game(player_name)

	if success:
		status_label.text = "房间已创建! 等待玩家加入..."
		visible = false
		mouse_filter = MOUSE_FILTER_IGNORE
	else:
		status_label.text = "创建房间失败!"

func _on_join_btn_pressed():
	if not multiplayer_manager:
		status_label.text = "错误: 多人管理器未找到!"
		return

	var player_name = player_name_input.text
	var ip = ip_input.text

	if player_name.is_empty():
		player_name = "Player"
	if ip.is_empty():
		ip = "127.0.0.1"

	status_label.text = "正在连接 " + ip + "..."
	var success = multiplayer_manager.join_game(ip, player_name)

	if success:
		status_label.text = "连接中..."
		# 直接隐藏
		visible = false
		mouse_filter = MOUSE_FILTER_IGNORE
	else:
		status_label.text = "连接失败!"

func _on_player_connected(peer_id: int):
	status_label.text = "玩家加入: " + str(peer_id)

func _on_player_disconnected(peer_id: int):
	status_label.text = "玩家离开: " + str(peer_id)

func _on_connection_failed():
	status_label.text = "连接失败!"

func _on_game_started():
	visible = false
	mouse_filter = MOUSE_FILTER_IGNORE
