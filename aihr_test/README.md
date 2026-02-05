# AI 面试系统

基于语音的 AI 面试应用，支持实时语音识别、智能追问、语音合成。通过 AI 面试官对求职者进行初步筛选，评估真实能力。

## 功能特点

- **实时语音交互**：支持语音输入和语音输出，模拟真实面试场景
- **智能追问**：AI 面试官根据回答质量进行针对性追问
- **能力评估**：实时评估候选人能力，给出分数和评语
- **自然对话**：面试官对话风格自然，避免机械式提问
- **流式处理**：LLM 流式生成 → 实时分句 → TTS 流式合成，降低延迟

## 技术架构

### 后端 (Python + FastAPI)

- **ASR 服务**：基于 DashScope qwen3-asr-flash-realtime 实现实时语音识别
- **LLM 服务**：基于 DashScope qwen-plus 实现智能对话
- **TTS 服务**：基于 DashScope qwen3-tts-flash-realtime 实现语音合成
- **面试逻辑**：评估-决策-追问循环，支持通过/不通过判定

### 前端 (Vue 3 + Vite)

- **语音录制**：Web Audio API 实现实时音频采集
- **音频播放**：Web Audio API 实现 PCM 音频播放
- **WebSocket**：实时双向通信
- **响应式界面**：现代化面试界面设计

## 项目结构

```
aihr_test/
├── backend/                    # 后端服务
│   ├── services/
│   │   ├── asr_service.py     # 语音识别服务
│   │   ├── tts_service.py     # 语音合成服务
│   │   ├── llm_service.py     # LLM 服务
│   │   └── interview_service.py # 面试逻辑服务
│   ├── config.py              # 配置管理
│   ├── main.py                # FastAPI 主入口
│   ├── requirements.txt
│   └── Dockerfile             # 后端容器配置
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   └── InterviewChat.vue  # 面试界面组件
│   │   ├── utils/
│   │   │   ├── websocket.js      # WebSocket 管理
│   │   │   ├── audioRecorder.js  # 音频录制
│   │   │   └── audioPlayer.js    # 音频播放
│   │   ├── styles/
│   │   │   └── main.css
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile             # 前端容器配置
├── docker-compose.yml         # Docker 编排配置
├── .dockerignore              # Docker 忽略文件
├── .env.example               # 环境变量示例
└── README.md
```

## 快速开始

### 方式一：Docker 部署（推荐）

确保已安装 Docker 和 Docker Compose。

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 2. 启动服务（支持热重载）
docker-compose up --build

# 后台运行
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务将在以下地址启动：
- 前端：http://localhost:5173
- 后端：http://localhost:8000

修改代码后会自动热重载，无需重启容器。

### 方式二：本地部署

#### 1. 环境准备

确保已安装：
- Python 3.9+
- Node.js 18+
- DashScope API Key（阿里云百炼平台）

#### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
DASHSCOPE_API_KEY=your_api_key_here
```

#### 3. 启动后端

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端服务将在 http://localhost:8000 启动

#### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 启动

### 开始面试

1. 打开浏览器访问 http://localhost:5173
2. 输入考察主题（如：React 框架、Java 并发编程等）
3. 点击"开始面试"
4. 按住麦克风按钮说话，或使用文字输入
5. AI 面试官会根据你的回答进行追问
6. 面试结束后会显示评估结果

## 面试流程

```
1. 开始面试
   ├── 设置考察主题
   └── AI 提出开场问题

2. 面试循环（3-5轮追问）
   ├── 候选人回答（语音/文字）
   ├── AI 评估回答质量
   ├── 决策判断
   │   ├── CONTINUE → 继续追问
   │   ├── PASS → 面试通过
   │   └── FAIL → 面试不通过
   └── 生成追问/结束语

3. 面试结束
   ├── 显示最终评分
   └── 显示评估说明
```

## 配置说明

### 面试参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| MIN_FOLLOWUP_QUESTIONS | 最少追问次数 | 3 |
| MAX_FOLLOWUP_QUESTIONS | 最大追问次数 | 5 |
| PASS_SCORE_THRESHOLD | 通过分数线 | 70 |

### 评分标准

- **优秀 (90-100)**：回答全面、有深度，有真实经验
- **良好 (70-89)**：基本概念清晰，有一定经验
- **及格 (60-69)**：了解基础知识，但缺乏深度
- **不及格 (0-59)**：概念模糊、逻辑混乱

## WebSocket 协议

### 客户端 → 服务端

| 消息类型 | 说明 |
|---------|------|
| `interview.start` | 开始面试 |
| `audio.input` | 发送音频数据 |
| `audio.end` | 结束音频输入 |
| `text.input` | 发送文本消息 |
| `interview.reset` | 重置面试 |

### 服务端 → 客户端

| 消息类型 | 说明 |
|---------|------|
| `session.created` | 会话创建 |
| `interview.started` | 面试开始 |
| `transcription.partial` | 实时识别中间结果 |
| `transcription.final` | 最终识别结果 |
| `response.started` | 开始生成回复 |
| `response.delta` | 文本片段 |
| `response.done` | 生成完成 |
| `evaluation.update` | 评估更新 |
| `interview.finished` | 面试结束 |
| `audio.delta` | 音频数据 |
| `error` | 错误信息 |

## 注意事项

1. **麦克风权限**：首次使用需要授权麦克风权限
2. **网络要求**：需要稳定的网络连接访问 DashScope API
3. **浏览器兼容**：推荐使用 Chrome、Edge 等现代浏览器
4. **HTTPS**：生产环境部署时需要使用 HTTPS 以支持麦克风

## License

MIT License
