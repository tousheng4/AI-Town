# 赛博小镇 (HelloAgents AI Town)

基于 HelloAgents 框架的 AI 小镇模拟游戏，展示多智能体系统在游戏中的应用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 游戏引擎 | Godot 4.x (GDScript) |
| 后端框架 | FastAPI + Python 3.10+ |
| AI 框架 | LangChain |
| LLM | 智谱 GLM-4 / 阿里 Qwen (可配置) |
| 向量数据库 | Qdrant (情景记忆) |
| 键值存储 | Redis (短期记忆) |

## 功能特性

### NPC 系统
- 3 个可交互 NPC：张三 (Python工程师)、李四 (产品经理)、王五 (UI设计师)
- 每个 NPC 有独特的角色设定（职位、性格、说话风格、爱好）
- NPC 自主行为：定时更新对话内容

### 对话系统
- 玩家与 NPC 实时对话
- 基于 LangChain 的多 Agent 协作架构
- 支持 Supervisor 模式调度多个专业 Agent

### 记忆系统
- **短期记忆**：Redis 存储最近 10 条对话，2 小时过期
- **长期记忆**：Qdrant 向量数据库，支持语义检索
- 多玩家独立记忆（按 player_id 区分）

### 好感度系统
- 好感度范围 0-100，分为 5 个等级
- LLM 分析对话情感自动调整
- 持久化存储

### 多人游戏
- 主机创建房间 / 客户端加入房间
- 玩家位置同步
- 最多 4 名玩家

## 项目结构

```
Helloagents-AI-Town/
├── backend/                    # Python 后端
│   ├── agent_framework/        # Agent 框架
│   │   ├── supervisor.py       # 调度器
│   │   ├── dialogue_agent.py   # 对话 Agent
│   │   ├── memory_agent.py     # 记忆 Agent
│   │   ├── affinity_agent.py   # 好感度 Agent
│   │   └── reflection_agent.py # 反思 Agent
│   ├── memory/                 # 记忆系统
│   │   ├── short_term.py      # 短期记忆 (Redis)
│   │   └── redis_client.py     # Redis 客户端
│   ├── relationship/           # 好感度系统
│   │   └── manager.py         # 好感度管理
│   ├── tests/                  # 测试工具
│   ├── main.py                 # FastAPI 主程序
│   ├── agents.py               # NPC Agent 管理器
│   ├── config.py               # 配置文件
│   ├── models.py               # 数据模型
│   └── state_manager.py        # NPC 状态管理
│
├── helloagents-ai-town/        # Godot 前端
│   ├── scripts/                # GDScript 脚本
│   │   ├── main.gd            # 主场景
│   │   ├── player.gd          # 玩家控制
│   │   ├── npc.gd             # NPC 控制
│   │   ├── dialogue_ui.gd     # 对话界面
│   │   ├── api_client.gd      # API 客户端
│   │   ├── config.gd          # 全局配置
│   │   ├── login.gd           # 登录界面
│   │   ├── multiplayer_manager.gd # 多人游戏管理
│   │   └── websocket_client.gd    # WebSocket 客户端
│   ├── scenes/                 # 游戏场景
│   └── assets/                 # 游戏资源
│
├── .env                        # 环境变量
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下必填项：

```env
# LLM 配置
LLM_MODEL_ID=glm-4
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 可选：Qdrant 向量数据库
QDRANT_URL=https://your-cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-key

# 可选：Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. 启动后端

```bash
python main.py
```

服务启动后访问：
- API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 4. 启动前端

1. 启动 Godot 4.x
2. 打开项目：`helloagents-ai-town/project.godot`
3. 按 F5 运行

### 5. 游戏操作

| 按键 | 功能 |
|------|------|
| W/A/S/D | 移动玩家 |
| E | 与 NPC 交互 |
| Enter | 发送消息 |
| ESC | 关闭对话框 |

## API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/chat` | POST | 与 NPC 对话 |
| `/npcs` | GET | 获取 NPC 列表 |
| `/npcs/status` | GET | 获取 NPC 状态 |
| `/npcs/{name}/memories` | GET | 获取 NPC 记忆 |
| `/npcs/{name}/affinity` | GET | 获取好感度 |

## 多人游戏

### 创建房间（主机）
1. 运行游戏
2. 点击「创建房间」
3. 输入玩家名称
4. 等待其他玩家加入

### 加入房间（客户端）
1. 运行游戏
2. 点击「加入房间」
3. 输入主机 IP 地址和玩家名称
4. 连接成功后进入游戏

## 数据流

```
玩家输入 → Godot前端 → HTTP请求 → FastAPI后端
                                          ↓
                                    Supervisor Agent
                                    /      |      \
                              Memory   Affinity  Dialogue
                                Agent    Agent     Agent
                                          ↓
                                    生成回复
                                          ↓
                                  HTTP响应 → Godot前端 → 显示对话
```

## 日志

对话日志保存在 `backend/logs/` 目录，按日期命名：
- `dialogue_2026-03-02.log`

## 文档

- [安装配置指南](SETUP_GUIDE.md)
- [对话日志系统](DIALOGUE_LOG_GUIDE.md)
- [好感度系统](AFFINITY_SYSTEM_GUIDE.md)
- [记忆系统](MEMORY_SYSTEM_GUIDE.md)

## License

MIT
