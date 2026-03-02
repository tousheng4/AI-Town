# 玩家控制脚本
extends CharacterBody2D

# 移动速度
@export var speed: float = 200.0

# 玩家信息 (用于多人同步)
var player_name: String = "Player"
var player_color: Color = Color.WHITE
var peer_id: int = 1  # 网络peer ID，默认1

# 当前可交互的NPC
var nearby_npc: Node = null

# 交互状态 (交互时禁用移动)
var is_interacting: bool = false

# 节点引用
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var camera: Camera2D = $Camera2D

# 音效引用
@onready var interact_sound: AudioStreamPlayer = null  # 交互音效
@onready var running_sound: AudioStreamPlayer = null  # 走路音效

# 走路音效状态
var is_playing_running_sound: bool = false

# 是否正在多人游戏中
var is_multiplayer: bool = false

func _ready():
	# 添加到player组 (重要!NPC需要通过这个组来识别玩家)
	add_to_group("player")

	# 获取音效节点 (可选,如果不存在也不会报错)
	interact_sound = get_node_or_null("InteractSound")
	running_sound = get_node_or_null("RunningSound")

	if interact_sound:
		print("[INFO] 玩家交互音效已启用")
	else:
		print("[WARN] 玩家没有InteractSound节点,交互音效已禁用")

	if running_sound:
		print("[INFO] 玩家走路音效已启用")
	else:
		print("[WARN] 玩家没有RunningSound节点,走路音效已禁用")

	Config.log_info("玩家初始化完成")

	# 检查是否在多人模式
	is_multiplayer = multiplayer.get_multiplayer_peer() != null

	# 根据网络身份设置
	# 注意：这里只在没有设置时才获取默认值
	# 实际的 peer_id 会在 main.gd 中被正确设置
	if peer_id == 0:
		var unique_id = multiplayer.get_unique_id()
		if unique_id != 0:
			peer_id = unique_id
	# 如果是服务器，第一个玩家ID是1
	if peer_id == 0:
		peer_id = 1
	print("[INFO] 多人模式: peer_id = ", peer_id, " authority=", get_multiplayer_authority())

	# 设置当前玩家信息到Config（用于API请求区分多玩家）
	# 如果Config中还没有设置（单人模式），则使用默认值
	if Config.player_id == "" or Config.player_id == "player":
		Config.player_id = player_name
		Config.player_name = player_name

	# 只有本地玩家才启用相机 (拥有authority的才是本地)
	var is_local = not is_multiplayer or get_multiplayer_authority() == multiplayer.get_unique_id()
	if is_local:
		camera.enabled = true
	else:
		camera.enabled = false

	# 播放默认动画
	if animated_sprite and animated_sprite.sprite_frames != null:
		if animated_sprite.sprite_frames.has_animation("idle"):
			animated_sprite.play("idle")
		else:
			print("[WARN] 没有 idle 动画")
	else:
		print("[WARN] animated_sprite 或 sprite_frames 为空")

func _physics_process(_delta: float):
	# 多人模式: 只有拥有者才能控制移动
	if is_multiplayer:
		# 动态检查是否拥有 authority
		var unique_id = multiplayer.get_unique_id()
		if unique_id == 0:
			unique_id = 1  # 主机默认
		var my_authority = get_multiplayer_authority()

		if my_authority != unique_id:
			# 非本地玩家，只同步位置，不处理输入
			return

	# 调试
	if is_multiplayer:
		pass  # 位置会在 broadcast_position 中打印

	# 如果正在交互,禁用移动
	if is_interacting:
		velocity = Vector2.ZERO
		move_and_slide()
		# 播放idle动画
		if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
			animated_sprite.play("idle")
		# 停止走路音效 ⭐ 
		stop_running_sound()
		return

	# 获取输入方向
	# 获取输入方向
	var input_direction = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

	# 如果上面的方式不行，尝试直接使用按键
	if input_direction.length() == 0:
		input_direction = Vector2(
			(Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left")),
			(Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up"))
		)

	# 获取输入方向结束

	# 设置速度
	velocity = input_direction * speed

	# 移动
	move_and_slide()

	# 更新动画和朝向
	var anim_name = update_animation(input_direction)

	# 更新走路音效
	update_running_sound(input_direction)

	# 多人模式: 广播位置给其他玩家
	if is_multiplayer and is_networked():
		broadcast_position(anim_name)

func update_animation(direction: Vector2) -> String:
	"""更新角色动画 (支持4方向),返回当前动画名称"""
	if animated_sprite.sprite_frames == null:
		return ""

	var anim_name = "idle"

	# 根据移动方向播放动画
	if direction.length() > 0:
		# 移动中 - 判断主要方向
		if abs(direction.x) > abs(direction.y):
			# 左右移动
			if direction.x > 0:
				# 向右
				if animated_sprite.sprite_frames.has_animation("walk_right"):
					animated_sprite.play("walk_right")
					anim_name = "walk_right"
					animated_sprite.flip_h = false
				elif animated_sprite.sprite_frames.has_animation("walk"):
					animated_sprite.play("walk")
					anim_name = "walk"
					animated_sprite.flip_h = false
			else:
				# 向左
				if animated_sprite.sprite_frames.has_animation("walk_left"):
					animated_sprite.play("walk_left")
					anim_name = "walk_left"
					animated_sprite.flip_h = false
				elif animated_sprite.sprite_frames.has_animation("walk"):
					animated_sprite.play("walk")
					anim_name = "walk"
					animated_sprite.flip_h = true
		else:
			# 上下移动
			if direction.y > 0:
				# 向下
				if animated_sprite.sprite_frames.has_animation("walk_down"):
					animated_sprite.play("walk_down")
					anim_name = "walk_down"
				elif animated_sprite.sprite_frames.has_animation("walk"):
					animated_sprite.play("walk")
					anim_name = "walk"
			else:
				# 向上
				if animated_sprite.sprite_frames.has_animation("walk_up"):
					animated_sprite.play("walk_up")
					anim_name = "walk_up"
				elif animated_sprite.sprite_frames.has_animation("walk"):
					animated_sprite.play("walk")
					anim_name = "walk"
	else:
		# 静止
		if animated_sprite.sprite_frames.has_animation("idle"):
			animated_sprite.play("idle")
			anim_name = "idle"

	return anim_name

func _input(event: InputEvent):
	# 按E键与NPC交互
	# 检查E键 (KEY_E = 69)
	if event is InputEventKey:
		if event.pressed and not event.echo:
			if event.keycode == KEY_E or event.keycode == KEY_ENTER or event.is_action_pressed("ui_accept"):
				if nearby_npc != null:
					#标记输入事件为已处理，阻止传递到输入框
					get_viewport().set_input_as_handled()
					#调用NPC的方法隐藏交互提示框
					nearby_npc.hide_interaction_hint()
					interact_with_npc()
					print("[INFO] E键触发交互")
				else:
					print("[WARN] 没有附近的NPC可以交互")

func interact_with_npc():
	"""与附近的NPC交互"""
	if nearby_npc != null:
		# 播放交互音效 ⭐ 
		if interact_sound:
			interact_sound.play()

		Config.log_info("与NPC交互: " + nearby_npc.npc_name)
		# 发送信号给对话系统
		get_tree().call_group("dialogue_system", "start_dialogue", nearby_npc.npc_name)

func set_nearby_npc(npc: Node):
	"""设置附近的NPC"""
	nearby_npc = npc
	if npc != null:
		print("[INFO] ✅ 进入NPC范围: ", npc.npc_name)
		Config.log_info("进入NPC范围: " + npc.npc_name)
	else:
		print("[INFO] ❌ 离开NPC范围")
		Config.log_info("离开NPC范围")

func get_nearby_npc() -> Node:
	"""获取附近的NPC"""
	return nearby_npc

func set_interacting(interacting: bool):
	"""设置交互状态"""
	is_interacting = interacting
	if interacting:
		print("[INFO] 🔒 玩家进入交互状态,移动已禁用")
		# 停止走路音效 ⭐ 
		stop_running_sound()
	else:
		print("[INFO] 🔓 玩家退出交互状态,移动已启用")

# ⭐ 更新走路音效
func update_running_sound(direction: Vector2):
	"""更新走路音效"""
	if running_sound == null:
		return

	# 如果正在移动
	if direction.length() > 0:
		# 如果音效还没播放,开始播放
		if not is_playing_running_sound:
			running_sound.play()
			is_playing_running_sound = true
			print("[INFO] 🎵 开始播放走路音效")
	else:
		# 如果停止移动,停止音效
		stop_running_sound()

# ⭐ 停止走路音效
func stop_running_sound():
	"""停止走路音效"""
	if running_sound and is_playing_running_sound:
		running_sound.stop()
		is_playing_running_sound = false
		print("[INFO] 🔇 停止走路音效")

# ========== 多人网络同步方法 ==========

func is_networked() -> bool:
	"""检查是否拥有这个玩家的网络控制权"""
	# 如果不是多人模式，返回false
	if not is_multiplayer:
		return false
	# 检查多人模式是否激活
	if not multiplayer.has_multiplayer_peer():
		return false
	# 获取peer id
	var unique_id = multiplayer.get_unique_id()
	if unique_id == 0:
		return false
	return get_multiplayer_authority() == unique_id

func set_player_info(name: String, color: Color):
	"""设置玩家信息"""
	player_name = name
	player_color = color

# 同步位置 (从服务器接收其他玩家的位置)
@rpc("reliable")
func sync_position(new_position: Vector2, anim_name: String, flip_h: bool):
	"""同步位置和动画 (被其他玩家调用)"""
	position = new_position
	if animated_sprite.sprite_frames and animated_sprite.sprite_frames.has_animation(anim_name):
		animated_sprite.play(anim_name)
		animated_sprite.flip_h = flip_h

# 同步玩家信息
@rpc("reliable")
func sync_player_info(name: String, color: Color):
	"""同步玩家信息"""
	player_name = name
	player_color = color

func broadcast_position(anim_name: String):
	"""广播位置给其他玩家"""
	# 多人模式下通过 multiplayer_manager 广播
	var mm = get_node_or_null("/root/MultiplayerManager")
	if mm and is_networked():
		var my_network_id = multiplayer.get_unique_id()

		# 只广播自己的位置（peer_id 应该等于自己的网络ID）
		if peer_id == my_network_id:
			# 只在不是主机时向服务器发送（主机直接在本地转发）
			if my_network_id != 1:
				mm.rpc_id(1, "broadcast_player_position", peer_id, position, anim_name, animated_sprite.flip_h)
			else:
				# 主机直接调用（不在 RPC 中）
				mm.broadcast_to_others(peer_id, position, anim_name, animated_sprite.flip_h)
