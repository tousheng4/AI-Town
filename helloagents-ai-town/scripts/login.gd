# 登录场景脚本
extends Control

# UI 元素引用
@onready var username_input: LineEdit = $VBoxContainer/FormContainer/UsernameInput
@onready var password_input: LineEdit = $VBoxContainer/FormContainer/PasswordInput
@onready var name_input: LineEdit = $VBoxContainer/FormContainer/NameInput
@onready var login_button: Button = $VBoxContainer/ButtonContainer/LoginButton
@onready var register_button: Button = $VBoxContainer/ButtonContainer/RegisterButton
@onready var status_label: Label = $VBoxContainer/StatusLabel
@onready var loading_indicator: Control = $VBoxContainer/LoadingIndicator

# 信号：登录成功
signal login_success(player_id: String, token: String, name: String)

func _ready():
	# 连接按钮信号
	login_button.pressed.connect(_on_login_button_pressed)
	register_button.pressed.connect(_on_register_button_pressed)

	# 设置密码输入框为密码模式
	password_input.secret = true

	# 默认隐藏加载指示器和状态
	if loading_indicator:
		loading_indicator.visible = false
	status_label.text = ""

	# 聚焦用户名输入框
	username_input.grab_focus()

func _on_login_button_pressed():
	var username = username_input.text.strip_edges()
	var password = password_input.text

	if username.is_empty() or password.is_empty():
		_show_error("请输入用户名和密码")
		return

	_set_loading(true)
	_do_login(username, password)

func _on_register_button_pressed():
	var username = username_input.text.strip_edges()
	var password = password_input.text
	var name = name_input.text.strip_edges()

	if username.is_empty() or password.is_empty():
		_show_error("请输入用户名和密码")
		return

	if password.length() < 6:
		_show_error("密码长度至少6位")
		return

	_set_loading(true)
	_do_register(username, password, name)

func _do_login(username: String, password: String):
	var url = Config.API_AUTH_LOGIN
	var body = JSON.stringify({
		"username": username,
		"password": password
	})

	var http_request = HTTPRequest.new()
	add_child(http_request)
	http_request.request_completed.connect(_on_login_request_completed)

	var error = http_request.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, body)
	if error != OK:
		_show_error("请求失败: " + str(error))
		_set_loading(false)

func _on_login_request_completed(result, response_code, headers, body):
	_set_loading(false)

	# 清理 HTTP 请求
	var http_request = get_child(0)
	if http_request is HTTPRequest:
		http_request.queue_free()

	if response_code == 200:
		var json = JSON.new()
		var parse_result = json.parse(body.get_string_from_utf8())
		if parse_result == OK:
			var data = json.data
			var token = data.get("access_token", "")
			var player_id = data.get("player_id", "")
			var name = data.get("name", "游客")

			if token and player_id:
				# 保存登录信息
				Config.auth_token = token
				Config.player_id = player_id
				Config.player_name = name

				print("[INFO] 登录成功: ", player_id)
				login_success.emit(player_id, token, name)
			else:
				_show_error("登录响应数据格式错误")
		else:
			_show_error("解析响应失败")
	elif response_code == 401:
		_show_error("用户名或密码错误")
	elif response_code == 400:
		_show_error("请求格式错误")
	else:
		_show_error("登录失败: " + str(response_code))

func _do_register(username: String, password: String, name: String):
	var url = Config.API_AUTH_REGISTER
	var body = JSON.stringify({
		"username": username,
		"password": password,
		"name": name if not name.is_empty() else null
	})

	var http_request = HTTPRequest.new()
	add_child(http_request)
	http_request.request_completed.connect(_on_register_request_completed)

	var error = http_request.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, body)
	if error != OK:
		_show_error("请求失败: " + str(error))
		_set_loading(false)

func _on_register_request_completed(result, response_code, headers, body):
	_set_loading(false)

	# 清理 HTTP 请求
	var http_request = get_child(0)
	if http_request is HTTPRequest:
		http_request.queue_free()

	if response_code == 200:
		var json = JSON.new()
		var parse_result = json.parse(body.get_string_from_utf8())
		if parse_result == OK:
			var data = json.data
			var token = data.get("access_token", "")
			var player_id = data.get("player_id", "")
			var player_name = data.get("name", username_input.text)

			if token and player_id:
				# 保存登录信息
				Config.auth_token = token
				Config.player_id = player_id
				Config.player_name = player_name

				print("[INFO] 注册成功: ", player_id)
				login_success.emit(player_id, token, player_name)
			else:
				_show_error("注册响应数据格式错误")
		else:
			_show_error("解析响应失败")
	elif response_code == 400:
		var json = JSON.new()
		var parse_result = json.parse(body.get_string_from_utf8())
		if parse_result == OK:
			var data = json.data
			var detail = data.get("detail", "注册失败")
			_show_error(detail)
		else:
			_show_error("注册失败: 用户名已存在")
	else:
		_show_error("注册失败: " + str(response_code))

func _show_error(message: String):
	status_label.text = message
	status_label.modulate = Color(1, 0.3, 0.3)  # 红色

func _show_success(message: String):
	status_label.text = message
	status_label.modulate = Color(0.3, 1, 0.3)  # 绿色

func _set_loading(is_loading: bool):
	loading_indicator.visible = is_loading
	login_button.disabled = is_loading
	register_button.disabled = is_loading
	username_input.editable = not is_loading
	password_input.editable = not is_loading
	name_input.editable = not is_loading
