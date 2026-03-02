# WebSocket 客户端 - 与后端实时通信
extends Node

# 信号定义
signal ws_connected()
signal ws_disconnected()
signal ws_player_joined(player_data: Dictionary)
signal ws_player_left(player_id: String)
signal ws_player_moved(player_data: Dictionary)
signal ws_npc_state_updated(npc_data: Dictionary)
signal ws_error(error_message: String)

# WebSocket 客户端
var ws_peer: WebSocketPeer

# 连接状态
var is_connected: bool = false
var reconnect_timer: float = 0.0
var reconnect_interval: float = 5.0  # 重连间隔(秒)

# 当前玩家ID
var current_player_id: String = ""

# 消息类型常量
const MSG_PLAYER_JOIN = "player_join"
const MSG_PLAYER_LEAVE = "player_leave"
const MSG_PLAYER_MOVE = "player_move"
const MSG_PLAYER_STATE = "player_state"
const MSG_NPC_STATE = "npc_state"
const MSG_CHAT_MESSAGE = "chat_message"
const MSG_CHAT_RESPONSE = "chat_response"
const MSG_ERROR = "error"


func _ready():
	print("[INFO] WebSocket 客户端初始化完成")


func _process(delta: float):
	# 处理 WebSocket 消息
	if is_connected and ws_peer:
		ws_peer.poll()
		var packet = ws_peer.get_packet()
		while packet.size() > 0:
			_handle_packet(packet)
			packet = ws_peer.get_packet()

		# 检查连接状态
		var state = ws_peer.get_ready_state()
		if state != WebSocketPeer.STATE_OPEN:
			is_connected = false
			ws_disconnected.emit()
			print("[WARN] WebSocket 连接断开，尝试重连...")

	# 自动重连
	if not is_connected:
		reconnect_timer += delta
		if reconnect_timer >= reconnect_interval:
			reconnect_timer = 0.0
			if current_player_id != "":
				connect_to_server(current_player_id)


func connect_to_server(player_id: String) -> void:
	"""连接到 WebSocket 服务器

	Args:
		player_id: 玩家ID
	"""
	current_player_id = player_id

	# 创建 WebSocketPeer
	ws_peer = WebSocketPeer.new()

	var url = Config.WS_BASE_URL + Config.WS_ENDPOINT + player_id
	print("[INFO] 连接 WebSocket: ", url)

	var err = ws_peer.connect_to_url(url)
	if err != OK:
		print("[ERROR] WebSocket 连接失败: ", err)
		ws_error.emit("连接失败: " + str(err))
		return

	print("[INFO] WebSocket 正在连接...")


func disconnect_from_server() -> void:
	"""断开 WebSocket 连接"""
	if ws_peer:
		ws_peer.close()
		ws_peer = null
	is_connected = false
	current_player_id = ""


func send_message(msg_type: String, data: Dictionary) -> bool:
	"""发送 WebSocket 消息

	Args:
		msg_type: 消息类型
		data: 消息数据

	Returns:
		是否发送成功
	"""
	if not is_connected or not ws_peer:
		return false

	var message = {
		"type": msg_type,
		"data": data
	}

	var json_string = JSON.stringify(message)
	ws_peer.send_text(json_string)
	return true


func send_player_move(x: float, y: float) -> bool:
	"""发送玩家移动消息

	Args:
		x: X坐标
		y: Y坐标

	Returns:
		是否发送成功
	"""
	return send_message(MSG_PLAYER_MOVE, {"x": x, "y": y})


func _handle_packet(packet: PackedByteArray) -> void:
	"""处理接收到的数据包

	Args:
		packet: 原始数据包
	"""
	var json = JSON.new()
	var parse_result = json.parse(packet.get_string_from_utf8())

	if parse_result != OK:
		print("[ERROR] 解析 WebSocket 消息失败")
		return

	var message = json.data
	if not message.has("type") or not message.has("data"):
		print("[ERROR] WebSocket 消息格式错误")
		return

	var msg_type = message["type"]
	var data = message["data"]

	match msg_type:
		MSG_PLAYER_JOIN:
			# 新玩家加入
			is_connected = true
			ws_connected.emit()
			ws_player_joined.emit(data)

		MSG_PLAYER_LEAVE:
			# 玩家离开
			var player_id = data.get("player_id", "")
			ws_player_left.emit(player_id)

		MSG_PLAYER_STATE:
			# 玩家状态更新
			ws_player_moved.emit(data)

		MSG_NPC_STATE:
			# NPC状态更新
			ws_npc_state_updated.emit(data)

		MSG_ERROR:
			# 错误消息
			var error_msg = data.get("message", "未知错误")
			ws_error.emit(error_msg)

		_:
			print("[WARN] 未知消息类型: ", msg_type)
