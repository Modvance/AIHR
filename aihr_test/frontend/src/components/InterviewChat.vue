<template>
  <div class="interview-container">
    <!-- 头部 -->
    <header class="interview-header">
      <div class="header-content">
        <h1>AI 面试系统</h1>
        <div class="connection-status" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          {{ isConnected ? '已连接' : '未连接' }}
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="interview-main">
      <!-- 面试设置面板（未开始时显示） -->
      <div v-if="!interviewStarted" class="setup-panel fade-in">
        <div class="setup-card">
          <h2>开始面试</h2>
          <p class="setup-description">请配置面试参数后开始面试</p>
          
          <div class="form-group">
            <label>考察主题 *</label>
            <input 
              v-model="interviewTopic" 
              type="text" 
              placeholder="例如：React 框架、Java 并发编程、系统设计等"
            />
          </div>
          
          <div class="form-group">
            <label>应聘岗位</label>
            <input 
              v-model="jobPosition" 
              type="text" 
              placeholder="例如：前端工程师、后端开发、全栈工程师"
            />
          </div>
          
          <button 
            class="start-btn"
            :disabled="!canStartInterview"
            @click="startInterview"
          >
            <span class="btn-icon">🎯</span>
            开始面试
          </button>
        </div>
      </div>

      <!-- 面试进行中 -->
      <div v-else class="interview-content">
        <!-- 面试信息栏 -->
        <div class="interview-info-bar">
          <div class="info-item">
            <span class="info-label">主题</span>
            <span class="info-value">{{ interviewTopic }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">进度</span>
            <span class="info-value">{{ followupCount }} / {{ maxFollowup }}</span>
          </div>
          <div v-if="currentScore > 0" class="info-item">
            <span class="info-label">评分</span>
            <span class="info-value score" :class="scoreClass">{{ currentScore }}</span>
          </div>
        </div>

        <!-- 消息列表 -->
        <div class="messages-container" ref="messagesContainer">
          <div 
            v-for="(message, index) in messages" 
            :key="index"
            class="message fade-in"
            :class="message.role"
          >
            <div class="message-avatar">
              {{ message.role === 'interviewer' ? '🤖' : '👤' }}
            </div>
            <div class="message-content">
              <div class="message-role">
                {{ message.role === 'interviewer' ? 'AI 面试官' : '我' }}
              </div>
              <div class="message-text" v-html="formatMessage(message.content)"></div>
            </div>
          </div>
          
          <!-- 实时识别文本 -->
          <div v-if="partialText" class="message candidate partial fade-in">
            <div class="message-avatar">👤</div>
            <div class="message-content">
              <div class="message-role">我 (识别中...)</div>
              <div class="message-text">{{ partialText }}</div>
            </div>
          </div>
          
          <!-- 处理中提示 -->
          <div v-if="isProcessing" class="message interviewer processing fade-in">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="message-role">AI 面试官</div>
              <div class="message-text typing">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 面试结果面板 -->
        <div v-if="interviewFinished" class="result-panel fade-in">
          <div class="result-card" :class="interviewResult">
            <div class="result-icon">
              {{ interviewResult === 'PASS' ? '🎉' : '📋' }}
            </div>
            <h3>{{ interviewResult === 'PASS' ? '面试通过' : '面试未通过' }}</h3>
            <div class="result-score">
              最终评分：<span>{{ finalScore }}</span> / 100
            </div>
            <p class="result-assessment">{{ finalAssessment }}</p>
            <button class="restart-btn" @click="resetInterview">
              重新开始
            </button>
          </div>
        </div>

        <!-- 输入区域 -->
        <div v-if="!interviewFinished" class="input-area">
          <!-- 语音输入 -->
          <div class="voice-input">
            <button 
              class="mic-btn"
              :class="{ recording: isRecording, disabled: isProcessing }"
              :disabled="isProcessing"
              @mousedown="startRecording"
              @mouseup="stopRecording"
              @mouseleave="stopRecording"
              @touchstart.prevent="startRecording"
              @touchend.prevent="stopRecording"
            >
              <span class="mic-icon">🎤</span>
              <span class="mic-text">{{ isRecording ? '松开结束' : '按住说话' }}</span>
            </button>
          </div>
          
          <!-- 文本输入（可选） -->
          <div class="text-input">
            <input 
              v-model="textInput"
              type="text"
              placeholder="或者输入文字回答..."
              :disabled="isProcessing"
              @keyup.enter="sendTextMessage"
            />
            <button 
              class="send-btn"
              :disabled="!textInput.trim() || isProcessing"
              @click="sendTextMessage"
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { WebSocketManager } from '../utils/websocket.js'
import { AudioRecorder } from '../utils/audioRecorder.js'
import { AudioPlayer } from '../utils/audioPlayer.js'

// 状态
const isConnected = ref(false)
const isRecording = ref(false)
const isProcessing = ref(false)
const interviewStarted = ref(false)
const interviewFinished = ref(false)

// 面试配置
const interviewTopic = ref('')
const jobPosition = ref('')

// 面试数据
const messages = ref([])
const partialText = ref('')
const currentScore = ref(0)
const followupCount = ref(0)
const maxFollowup = ref(5)

// 面试结果
const interviewResult = ref('')
const finalScore = ref(0)
const finalAssessment = ref('')

// 文本输入
const textInput = ref('')

// DOM 引用
const messagesContainer = ref(null)

// 工具实例
let wsManager = null
let audioRecorder = null
let audioPlayer = null

// 计算属性
const canStartInterview = computed(() => {
  return isConnected.value && interviewTopic.value.trim()
})

const scoreClass = computed(() => {
  if (currentScore.value >= 70) return 'good'
  if (currentScore.value >= 60) return 'medium'
  return 'low'
})

// 格式化消息（支持 Markdown）
const formatMessage = (content) => {
  if (!content) return ''
  return marked(content, { breaks: true })
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息变化自动滚动
watch(messages, scrollToBottom, { deep: true })
watch(partialText, scrollToBottom)

// 连接 WebSocket
const connectWebSocket = async () => {
  const wsUrl = `ws://${window.location.hostname}:8000/ws/interview`
  wsManager = new WebSocketManager(wsUrl)

  // 注册消息处理器
  wsManager.on('session.created', (data) => {
    console.log('Session created:', data.session_id)
    isConnected.value = true
  })

  wsManager.on('interview.started', (data) => {
    console.log('Interview started:', data)
    interviewStarted.value = true
  })

  wsManager.on('transcription.partial', (data) => {
    partialText.value = data.text
  })

  wsManager.on('transcription.final', (data) => {
    partialText.value = ''
    if (data.text) {
      messages.value.push({
        role: 'candidate',
        content: data.text
      })
    }
  })

  wsManager.on('response.started', () => {
    isProcessing.value = true
  })

  wsManager.on('response.delta', (data) => {
    // 更新最后一条面试官消息
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.role === 'interviewer' && lastMessage.isStreaming) {
      lastMessage.content += data.text
    } else {
      messages.value.push({
        role: 'interviewer',
        content: data.text,
        isStreaming: true
      })
    }
    scrollToBottom()
  })

  wsManager.on('response.done', (data) => {
    isProcessing.value = false
    // 标记消息流式结束
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.isStreaming) {
      lastMessage.isStreaming = false
    }
  })

  wsManager.on('evaluation.update', (data) => {
    currentScore.value = data.score
    followupCount.value = data.followup_count
    maxFollowup.value = data.max_followup
  })

  wsManager.on('interview.finished', (data) => {
    interviewFinished.value = true
    interviewResult.value = data.result
    finalScore.value = data.score
    finalAssessment.value = data.assessment
  })

  wsManager.on('audio.delta', async (data) => {
    const audioData = WebSocketManager.base64ToArrayBuffer(data.data)
    await audioPlayer.play(audioData)
  })

  wsManager.on('error', (data) => {
    console.error('Error:', data)
  })

  try {
    await wsManager.connect()
  } catch (error) {
    console.error('Failed to connect:', error)
  }
}

// 开始面试
const startInterview = () => {
  if (!canStartInterview.value) return
  
  wsManager.startInterview(
    interviewTopic.value,
    jobPosition.value
  )
}

// 开始录音
const startRecording = async () => {
  if (isProcessing.value || isRecording.value) return

  try {
    audioRecorder = new AudioRecorder({
      sampleRate: 16000,
      onAudioData: (pcmData) => {
        wsManager.sendAudio(pcmData)
      }
    })

    await audioRecorder.start()
    isRecording.value = true
  } catch (error) {
    console.error('Failed to start recording:', error)
    alert('无法访问麦克风，请检查权限设置')
  }
}

// 停止录音
const stopRecording = () => {
  if (!isRecording.value) return

  audioRecorder.stop()
  isRecording.value = false
  
  // 通知后端音频结束
  wsManager.endAudio()
}

// 发送文本消息
const sendTextMessage = () => {
  if (!textInput.value.trim() || isProcessing.value) return

  const text = textInput.value.trim()
  textInput.value = ''

  // 添加到消息列表
  messages.value.push({
    role: 'candidate',
    content: text
  })

  // 发送到后端
  wsManager.sendText(text)
}

// 重置面试
const resetInterview = () => {
  messages.value = []
  currentScore.value = 0
  followupCount.value = 0
  interviewFinished.value = false
  interviewResult.value = ''
  finalScore.value = 0
  finalAssessment.value = ''
  interviewStarted.value = false
  interviewTopic.value = ''
  jobPosition.value = ''
  
  wsManager.resetInterview()
  audioPlayer.stop()
}

// 生命周期
onMounted(async () => {
  audioPlayer = new AudioPlayer({ sampleRate: 24000 })
  await connectWebSocket()
})

onUnmounted(() => {
  if (wsManager) {
    wsManager.disconnect()
  }
  if (audioRecorder) {
    audioRecorder.stop()
  }
  if (audioPlayer) {
    audioPlayer.close()
  }
})
</script>

<style scoped>
.interview-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 头部 */
.interview-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}

.connection-status.connected .status-dot {
  background: #22c55e;
}

/* 主内容 */
.interview-main {
  flex: 1;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
}

/* 设置面板 */
.setup-panel {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.setup-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.setup-card h2 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #333;
}

.setup-description {
  color: #666;
  margin-bottom: 32px;
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: #667eea;
}

.start-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-size: 18px;
  font-weight: 600;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.start-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.start-btn:disabled {
  background: #ccc;
}

/* 面试内容 */
.interview-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}

/* 面试信息栏 */
.interview-info-bar {
  background: white;
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.info-value.score.good {
  color: #22c55e;
}

.info-value.score.medium {
  color: #f59e0b;
}

.info-value.score.low {
  color: #ef4444;
}

/* 消息列表 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message.candidate {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.message.candidate .message-avatar {
  background: #e0e7ff;
}

.message-content {
  max-width: 70%;
}

.message.candidate .message-content {
  text-align: right;
}

.message-role {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.message-text {
  background: #f3f4f6;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
}

.message.candidate .message-text {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.message.partial .message-text {
  background: #fef3c7;
  color: #92400e;
}

/* 打字动画 */
.typing {
  display: flex;
  gap: 4px;
  padding: 8px 16px;
}

.typing .dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing .dot:nth-child(1) {
  animation-delay: 0s;
}

.typing .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
}

/* 结果面板 */
.result-panel {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.result-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.result-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.result-card h3 {
  font-size: 24px;
  margin-bottom: 16px;
}

.result-card.PASS h3 {
  color: #22c55e;
}

.result-card.FAIL h3 {
  color: #ef4444;
}

.result-score {
  font-size: 18px;
  margin-bottom: 16px;
}

.result-score span {
  font-weight: 700;
  font-size: 24px;
  color: #667eea;
}

.result-assessment {
  color: #666;
  margin-bottom: 24px;
  line-height: 1.6;
}

.restart-btn {
  padding: 12px 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}

.restart-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

/* 输入区域 */
.input-area {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.voice-input {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.mic-btn {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.mic-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.mic-btn.recording {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  animation: recording 1.5s infinite;
}

.mic-btn.disabled {
  background: #ccc;
}

.mic-icon {
  font-size: 32px;
}

.mic-text {
  font-size: 12px;
}

.text-input {
  display: flex;
  gap: 8px;
}

.text-input input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
}

.text-input input:focus {
  border-color: #667eea;
}

.send-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-weight: 600;
  border-radius: 8px;
}

.send-btn:disabled {
  background: #ccc;
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    padding: 12px 16px;
  }

  .header-content h1 {
    font-size: 20px;
  }

  .interview-main {
    padding: 16px;
  }

  .setup-card {
    padding: 24px;
  }

  .interview-info-bar {
    flex-wrap: wrap;
    gap: 16px;
  }

  .message-content {
    max-width: 85%;
  }

  .mic-btn {
    width: 100px;
    height: 100px;
  }

  .mic-icon {
    font-size: 28px;
  }
}
</style>
