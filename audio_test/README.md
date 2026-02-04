# AI 语音助手 - 实时语音交互系统

一个基于 DashScope（阿里云百炼）的实时语音交互 AI 系统，支持语音输入、智能对话、语音输出，类似于豆包或 ChatGPT 的语音聊天模式。

## 功能特性

- **实时语音识别 (ASR)**：基于 qwen3-asr-flash-realtime 模型，支持实时语音转文字
- **智能对话 (LLM)**：基于 qwen-plus 模型，支持流式输出，保持上下文对话
- **语音合成 (TTS)**：基于 qwen3-tts-flash-realtime 模型，使用 commit 模式实现低延迟语音合成
- **前后端分离**：Vue 3 前端 + FastAPI 后端
- **WebSocket 通信**：实现双向实时通信
- **美观的 UI**：现代化深色主题，响应式设计

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- WebSocket
- DashScope SDK

### 前端
- Vue 3
- Vite
- Web Audio API
- WebSocket

## 项目结构

```
audio_test/
├── backend/                 # 后端代码
│   ├── services/           # 服务模块
│   │   ├── __init__.py
│   │   ├── asr_service.py  # 语音识别服务
│   │   ├── llm_service.py  # 对话生成服务
│   │   └── tts_service.py  # 语音合成服务
│   ├── config.py           # 配置文件
│   ├── main.py             # 主入口
│   ├── requirements.txt    # Python 依赖
│   └── Dockerfile
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/
│   │   │   └── VoiceChat.vue  # 语音聊天组件
│   │   ├── utils/
│   │   │   ├── audioRecorder.js  # 音频录制
│   │   │   ├── audioPlayer.js    # 音频播放
│   │   │   └── websocket.js      # WebSocket 管理
│   │   ├── styles/
│   │   │   └── main.css
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── .env.example            # 环境变量示例
├── docker-compose.yml      # Docker 编排
├── .gitignore
└── README.md
```

## 快速开始

### 前提条件

1. 获取 DashScope API Key
   - 访问 [阿里云百炼](https://help.aliyun.com/zh/model-studio/get-api-key) 获取 API Key

2. 确保已安装：
   - Python 3.11+
   - Node.js 18+
   - 或 Docker & Docker Compose

### 方式一：本地运行

#### 1. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# DASHSCOPE_API_KEY=your-api-key
```

#### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

后端将在 `http://localhost:8000` 运行。

#### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 运行。

### 方式二：Docker 运行

```bash
# 设置环境变量
export DASHSCOPE_API_KEY=your-api-key

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 使用说明

1. 打开浏览器访问 `http://localhost:5173`
2. 等待连接建立（状态显示"已连接"）
3. 使用方式：
   - **语音输入**：按住麦克风按钮说话，松开后自动识别并获取 AI 回复
   - **文字输入**：在输入框输入文字，按回车或点击发送
4. AI 的回复会以文字和语音形式呈现

## WebSocket 消息协议

### 客户端发送

| 类型 | 描述 | 数据 |
|------|------|------|
| `audio.input` | 发送音频数据 | `{type, data: base64}` |
| `audio.end` | 结束音频输入 | `{type}` |
| `text.input` | 发送文本 | `{type, text}` |
| `clear.history` | 清空对话历史 | `{type}` |

### 服务端发送

| 类型 | 描述 | 数据 |
|------|------|------|
| `session.created` | 会话创建 | `{type, session_id}` |
| `transcription.partial` | 实时识别 | `{type, text}` |
| `transcription.final` | 最终识别 | `{type, text}` |
| `speech.started` | 检测到语音 | `{type}` |
| `speech.stopped` | 语音停止 | `{type}` |
| `response.started` | 开始生成 | `{type}` |
| `response.delta` | 文本片段 | `{type, text}` |
| `response.done` | 生成完成 | `{type, text}` |
| `audio.delta` | 音频数据 | `{type, data: base64}` |
| `audio.sentence.done` | 句子合成完成 | `{type}` |
| `audio.finished` | 全部合成完成 | `{type}` |
| `error` | 错误信息 | `{type, source, message}` |

## 配置选项

通过 `.env` 文件或环境变量配置：

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `DASHSCOPE_API_KEY` | - | DashScope API Key（必填） |
| `ASR_MODEL` | qwen3-asr-flash-realtime | ASR 模型 |
| `ASR_SAMPLE_RATE` | 16000 | 音频采样率 |
| `ASR_LANGUAGE` | zh | 识别语言 |
| `LLM_MODEL` | qwen-plus | LLM 模型 |
| `LLM_SYSTEM_PROMPT` | - | 系统提示词 |
| `TTS_MODEL` | qwen3-tts-flash-realtime | TTS 模型 |
| `TTS_VOICE` | Cherry | 语音音色 |
| `TTS_SAMPLE_RATE` | 24000 | 输出采样率 |
| `HOST` | 0.0.0.0 | 服务地址 |
| `PORT` | 8000 | 服务端口 |
| `CORS_ORIGINS` | localhost:5173,localhost:3000 | 允许的跨域来源 |

## 可用音色

TTS 支持以下音色：
- `Cherry` - 女声，温柔
- `Maia` - 女声，活泼
- `Ethan` - 男声
- 更多音色请参考 [DashScope TTS 文档](https://help.aliyun.com/document_detail/...)

## 注意事项

1. **浏览器权限**：首次使用需要授权麦克风权限
2. **HTTPS**：在非 localhost 环境使用麦克风需要 HTTPS
3. **API 配额**：请注意 DashScope API 的调用配额限制
4. **网络延迟**：语音交互的实时性受网络环境影响

## 常见问题

**Q: 无法录音？**
- 检查浏览器是否授权麦克风权限
- 检查是否使用 HTTPS 或 localhost

**Q: 连接失败？**
- 检查后端服务是否正常运行
- 检查 API Key 是否正确配置

**Q: 语音合成没有声音？**
- 检查浏览器是否静音
- 尝试点击页面后再操作（浏览器音频策略）

## License

MIT
