<template>
  <div class="voice-chat">
    <!-- 头部 -->
    <header class="chat-header">
      <div class="header-content">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <h1>AI 语音助手</h1>
        </div>
        <div class="connection-status" :class="connectionClass">
          <span class="status-dot"></span>
          <span class="status-text">{{ connectionText }}</span>
        </div>
      </div>
    </header>

    <!-- 消息列表 -->
    <main class="chat-messages" ref="messagesContainer" @scroll="handleScroll">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zm6 6a6 6 0 0 1-12 0H4a8 8 0 0 0 16 0h-2z"/>
            <path d="M12 18a8 8 0 0 1-8-8H2c0 4.97 3.67 9.08 8.44 9.83V22h3.12v-2.17C18.33 19.08 22 14.97 22 10h-2a8 8 0 0 1-8 8z"/>
          </svg>
        </div>
        <h2>开始语音对话</h2>
        <p>按住下方麦克风按钮开始说话，或者直接输入文字</p>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        class="message animate-slide-up"
        :class="message.role"
      >
        <div class="message-avatar">
          <svg v-if="message.role === 'user'" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="message-bubble">
            <span v-if="message.role === 'assistant'" class="message-text markdown-body" v-html="renderMarkdown(message.content)"></span>
            <span v-else class="message-text">{{ message.content }}</span>
            <span v-if="message.isStreaming" class="cursor">|</span>
          </div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
        </div>
      </div>

      <!-- 实时识别显示 -->
      <div v-if="partialText" class="message user partial animate-fade-in">
        <div class="message-avatar">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="message-bubble partial-bubble">
            {{ partialText }}
            <span class="recording-indicator"></span>
          </div>
        </div>
      </div>
    </main>

    <!-- 回到底部按钮 -->
    <button 
      v-show="showScrollButton" 
      class="scroll-to-bottom-btn"
      @click="scrollToBottomForce"
    >
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
      </svg>
      <span v-if="isProcessing">正在输出...</span>
    </button>

    <!-- 底部输入区域 -->
    <footer class="chat-footer">
      <!-- 状态提示 -->
      <div v-if="statusText" class="status-bar" :class="statusClass">
        {{ statusText }}
      </div>

      <div class="input-area">
        <!-- 文本输入 -->
        <div class="text-input-wrapper">
          <input
            v-model="textInput"
            type="text"
            placeholder="输入消息..."
            @keyup.enter="sendTextMessage"
            :disabled="!isConnected || isProcessing"
          />
          <button
            class="send-btn"
            @click="sendTextMessage"
            :disabled="!textInput.trim() || !isConnected || isProcessing"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>

        <!-- 语音按钮 -->
        <div class="voice-button-wrapper">
          <button
            class="voice-btn"
            :class="{ recording: isRecording, disabled: !isConnected || isProcessing }"
            @mousedown="startRecording"
            @mouseup="stopRecording"
            @mouseleave="stopRecording"
            @touchstart.prevent="startRecording"
            @touchend.prevent="stopRecording"
            :disabled="!isConnected || isProcessing"
          >
            <div class="ripple" v-if="isRecording"></div>
            <svg class="mic-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
            </svg>
          </button>
          <span class="voice-hint">{{ isRecording ? '松开发送' : '按住说话' }}</span>
        </div>

        <!-- 清空按钮 -->
        <button class="clear-btn" @click="clearHistory" title="清空对话">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
          </svg>
        </button>
      </div>
    </footer>

    <!-- 音频播放状态指示器 -->
    <div v-if="isPlayingAudio" class="audio-indicator">
      <div class="waveform">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
      <span>正在播放...</span>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { WebSocketManager } from '../utils/websocket'
import { AudioRecorder } from '../utils/audioRecorder'
import { AudioPlayer } from '../utils/audioPlayer'

// 配置 marked
marked.setOptions({
  breaks: true,  // 支持换行
  gfm: true      // 支持 GitHub 风格 Markdown
})

export default {
  name: 'VoiceChat',
  setup() {
    // 状态
    const isConnected = ref(false)
    const isRecording = ref(false)
    const isProcessing = ref(false)
    const isPlayingAudio = ref(false)
    const messages = ref([])
    const textInput = ref('')
    const partialText = ref('')
    const statusText = ref('')
    const statusClass = ref('')
    const messagesContainer = ref(null)
    const showScrollButton = ref(false)
    const userScrolledUp = ref(false)
    
    // 服务实例
    let wsManager = null
    let audioRecorder = null
    let audioPlayer = null
    
    // 当前流式响应的索引
    let streamingMessageIndex = -1
    
    // 打字机效果队列
    let typewriterQueue = []
    let isTyping = false
    
    // 打字机效果 - 逐字显示文本
    const typewriterEffect = async () => {
      if (isTyping || typewriterQueue.length === 0) return
      
      isTyping = true
      
      while (typewriterQueue.length > 0) {
        const char = typewriterQueue.shift()
        
        if (streamingMessageIndex >= 0 && streamingMessageIndex < messages.value.length) {
          // 直接通过索引访问并修改内容
          messages.value[streamingMessageIndex].content += char
        }
        
        // 控制打字速度
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      
      isTyping = false
      scrollToBottom()
    }
    
    // 连接状态
    const connectionClass = computed(() => ({
      connected: isConnected.value,
      disconnected: !isConnected.value
    }))
    
    const connectionText = computed(() => 
      isConnected.value ? '已连接' : '未连接'
    )
    
    // 格式化时间
    const formatTime = (timestamp) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }
    
    // 渲染 Markdown
    const renderMarkdown = (content) => {
      if (!content) return ''
      return marked(content)
    }
    
    // 检测是否接近底部（距离底部 10px 以内）
    const isNearBottom = () => {
      if (!messagesContainer.value) return true
      const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value
      return scrollHeight - scrollTop - clientHeight < 10
    }
    
    // 处理滚动事件
    const handleScroll = () => {
      if (isNearBottom()) {
        userScrolledUp.value = false
        showScrollButton.value = false
      } else {
        userScrolledUp.value = true
        showScrollButton.value = true
      }
    }
    
    // 滚动到底部（仅当用户未向上滚动时）
    const scrollToBottom = () => {
      if (userScrolledUp.value) return
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
    
    // 强制滚动到底部（用户点击按钮时）
    const scrollToBottomForce = () => {
      userScrolledUp.value = false
      showScrollButton.value = false
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
    
    // 添加消息
    const addMessage = (role, content, isStreaming = false) => {
      const message = {
        role,
        content,
        timestamp: Date.now(),
        isStreaming
      }
      messages.value.push(message)
      scrollToBottom()
      return message
    }
    
    // 更新状态
    const setStatus = (text, className = '') => {
      statusText.value = text
      statusClass.value = className
      if (text) {
        setTimeout(() => {
          if (statusText.value === text) {
            statusText.value = ''
            statusClass.value = ''
          }
        }, 3000)
      }
    }
    
    // 初始化 WebSocket
    const initWebSocket = async () => {
      wsManager = new WebSocketManager({
        onConnect: () => {
          isConnected.value = true
          setStatus('连接成功', 'success')
        },
        onDisconnect: () => {
          isConnected.value = false
          setStatus('连接断开，正在重连...', 'warning')
        },
        onError: (error) => {
          setStatus('连接错误', 'error')
          console.error('WebSocket error:', error)
        }
      })
      
      // 注册消息处理器
      wsManager.on('transcription.partial', (msg) => {
        partialText.value = msg.text
      })
      
      wsManager.on('transcription.final', (msg) => {
        partialText.value = ''
        if (msg.text) {
          addMessage('user', msg.text)
        }
      })
      
      wsManager.on('speech.started', () => {
        setStatus('正在录音...', 'info')
      })
      
      wsManager.on('speech.stopped', () => {
        setStatus('识别中...', 'info')
      })
      
      wsManager.on('response.started', () => {
        isProcessing.value = true
        // 清空打字机队列
        typewriterQueue = []
        isTyping = false
        // 添加消息并记录索引
        addMessage('assistant', '', true)
        streamingMessageIndex = messages.value.length - 1
        setStatus('AI 正在回复...', 'info')
      })
      
      wsManager.on('response.delta', (msg) => {
        if (streamingMessageIndex >= 0 && msg.text) {
          // 将文本拆分为字符并加入队列
          for (const char of msg.text) {
            typewriterQueue.push(char)
          }
          // 启动打字机效果
          typewriterEffect()
        }
      })
      
      wsManager.on('response.done', async (msg) => {
        // 等待打字机效果完成
        while (typewriterQueue.length > 0 || isTyping) {
          await new Promise(resolve => setTimeout(resolve, 50))
        }
        
        if (streamingMessageIndex >= 0 && streamingMessageIndex < messages.value.length) {
          messages.value[streamingMessageIndex].isStreaming = false
        }
        streamingMessageIndex = -1
        isProcessing.value = false
        setStatus('', '')
      })
      
      wsManager.on('audio.delta', async (msg) => {
        // 播放音频
        const audioData = wsManager.base64ToArrayBuffer(msg.data)
        await audioPlayer.addPCMData(audioData)
        isPlayingAudio.value = true
      })
      
      wsManager.on('audio.finished', () => {
        // 音频播放完成会通过 AudioPlayer 的回调处理
      })
      
      wsManager.on('history.cleared', () => {
        messages.value = []
        setStatus('对话已清空', 'success')
      })
      
      wsManager.on('error', (msg) => {
        setStatus(`错误: ${msg.message}`, 'error')
        isProcessing.value = false
      })
      
      try {
        await wsManager.connect()
      } catch (error) {
        console.error('Failed to connect:', error)
        setStatus('连接失败，请刷新页面重试', 'error')
      }
    }
    
    // 初始化音频录制器
    const initAudioRecorder = async () => {
      audioRecorder = new AudioRecorder({
        sampleRate: 16000,
        onAudioData: (pcmData) => {
          if (wsManager && wsManager.isConnected) {
            wsManager.sendAudio(pcmData)
          }
        },
        onError: (error) => {
          setStatus('麦克风访问失败', 'error')
          console.error('Audio recorder error:', error)
        }
      })
      
      const success = await audioRecorder.init()
      if (!success) {
        setStatus('无法访问麦克风，请检查权限设置', 'error')
      }
    }
    
    // 初始化音频播放器
    const initAudioPlayer = async () => {
      audioPlayer = new AudioPlayer({
        sampleRate: 24000,
        onPlayStart: () => {
          isPlayingAudio.value = true
        },
        onPlayEnd: () => {
          isPlayingAudio.value = false
        },
        onError: (error) => {
          console.error('Audio player error:', error)
        }
      })
      
      await audioPlayer.init()
    }
    
    // 开始录音
    const startRecording = async () => {
      if (!isConnected.value || isProcessing.value || isRecording.value) return
      
      // 停止当前正在播放的音频
      if (audioPlayer && audioPlayer.playing) {
        audioPlayer.stop()
      }
      
      if (!audioRecorder) {
        await initAudioRecorder()
      }
      
      if (audioRecorder && audioRecorder.start()) {
        isRecording.value = true
        setStatus('正在录音...', 'info')
      }
    }
    
    // 停止录音
    const stopRecording = () => {
      if (!isRecording.value) return
      
      isRecording.value = false
      partialText.value = ''
      
      if (audioRecorder) {
        audioRecorder.stop()
      }
      
      // 通知服务端音频结束
      if (wsManager) {
        wsManager.endAudio()
        setStatus('识别中...', 'info')
      }
    }
    
    // 发送文本消息
    const sendTextMessage = () => {
      const text = textInput.value.trim()
      if (!text || !isConnected.value || isProcessing.value) return
      
      // 停止当前正在播放的音频
      if (audioPlayer && audioPlayer.playing) {
        audioPlayer.stop()
      }
      
      addMessage('user', text)
      wsManager.sendText(text)
      textInput.value = ''
    }
    
    // 清空对话历史
    const clearHistory = () => {
      if (wsManager) {
        wsManager.clearHistory()
      }
    }
    
    // 生命周期
    onMounted(async () => {
      await initWebSocket()
      await initAudioPlayer()
    })
    
    onUnmounted(() => {
      if (audioRecorder) {
        audioRecorder.destroy()
      }
      if (audioPlayer) {
        audioPlayer.destroy()
      }
      if (wsManager) {
        wsManager.disconnect()
      }
    })
    
    // 监听消息变化，自动滚动
    watch(messages, scrollToBottom, { deep: true })
    
    return {
      isConnected,
      isRecording,
      isProcessing,
      isPlayingAudio,
      messages,
      textInput,
      partialText,
      statusText,
      statusClass,
      messagesContainer,
      showScrollButton,
      connectionClass,
      connectionText,
      formatTime,
      renderMarkdown,
      handleScroll,
      scrollToBottomForce,
      startRecording,
      stopRecording,
      sendTextMessage,
      clearHistory
    }
  }
}
</script>

<style scoped>
.voice-chat {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--background-color);
  position: relative;
}

/* 头部 */
.chat-header {
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  padding: 1rem 1.5rem;
  flex-shrink: 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: var(--gradient-primary);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.logo-icon svg {
  width: 24px;
  height: 24px;
}

.logo h1 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
}

.connection-status.connected {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success-color);
}

.connection-status.disconnected {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.connected .status-dot {
  animation: pulse 2s infinite;
}

/* 消息区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: var(--surface-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
}

.empty-icon svg {
  width: 40px;
  height: 40px;
  color: var(--primary-color);
}

.empty-state h2 {
  font-size: 1.25rem;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-state p {
  font-size: 0.875rem;
}

/* 消息样式 */
.message {
  display: flex;
  gap: 0.75rem;
  max-width: 80%;
}

.message.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: var(--user-bubble);
  color: white;
}

.message.assistant .message-avatar {
  background: var(--surface-light);
  color: var(--primary-color);
}

.message-avatar svg {
  width: 20px;
  height: 20px;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.message-bubble {
  padding: 0.875rem 1rem;
  border-radius: 16px;
  line-height: 1.5;
  word-break: break-word;
}

.message.user .message-bubble {
  background: var(--user-bubble);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: var(--assistant-bubble);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.message.partial .message-bubble {
  background: var(--surface-light);
  opacity: 0.8;
}

.partial-bubble {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.recording-indicator {
  width: 8px;
  height: 8px;
  background: var(--error-color);
  border-radius: 50%;
  animation: pulse 1s infinite;
}

.message-time {
  font-size: 0.75rem;
  color: var(--text-muted);
  padding: 0 0.5rem;
}

.message.user .message-time {
  text-align: right;
}

/* 消息文本 */
.message-text {
  white-space: pre-wrap;
}

/* Markdown 样式 */
.markdown-body {
  line-height: 1.5;
}

.markdown-body :deep(p) {
  margin: 0.25em 0;
}

.markdown-body :deep(p:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.75em;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.3em 0;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.2em 0;
  padding-left: 1.2em;
}

.markdown-body :deep(li) {
  margin: 0.1em 0;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--primary-color);
  margin: 0.3em 0;
  padding-left: 0.75em;
  color: var(--text-secondary);
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 0.3em 0 0.2em 0;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: var(--primary-color);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

/* 打字光标 */
.cursor {
  display: inline;
  font-weight: bold;
  animation: blink 0.7s infinite;
  margin-left: 1px;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* 底部输入区域 */
.chat-footer {
  background: var(--surface-color);
  border-top: 1px solid var(--border-color);
  padding: 1rem 1.5rem;
  flex-shrink: 0;
}

.status-bar {
  text-align: center;
  padding: 0.5rem;
  margin-bottom: 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
}

.status-bar.info {
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary-color);
}

.status-bar.success {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success-color);
}

.status-bar.warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning-color);
}

.status-bar.error {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error-color);
}

.input-area {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

.text-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background: var(--surface-light);
  border-radius: 24px;
  padding: 0.5rem 0.5rem 0.5rem 1rem;
  border: 1px solid var(--border-color);
  transition: border-color 0.2s;
}

.text-input-wrapper:focus-within {
  border-color: var(--primary-color);
}

.text-input-wrapper input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 1rem;
  padding: 0.5rem 0;
}

.text-input-wrapper input::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-color);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s, transform 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn svg {
  width: 20px;
  height: 20px;
}

/* 语音按钮 */
.voice-button-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.voice-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--gradient-primary);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: var(--shadow-lg);
}

.voice-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.voice-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.voice-btn.recording {
  background: var(--error-color);
  animation: recording-pulse 1.5s infinite;
}

.voice-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes recording-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5);
  }
  50% {
    box-shadow: 0 0 0 20px rgba(239, 68, 68, 0);
  }
}

.voice-btn .ripple {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  animation: ripple 1s infinite;
}

.mic-icon {
  width: 28px;
  height: 28px;
  z-index: 1;
}

.voice-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* 清空按钮 */
.clear-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--surface-light);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: var(--error-color);
  border-color: var(--error-color);
  color: white;
}

.clear-btn svg {
  width: 20px;
  height: 20px;
}

/* 回到底部按钮 */
.scroll-to-bottom-btn {
  position: absolute;
  bottom: 120px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-lg);
  z-index: 10;
}

.scroll-to-bottom-btn:hover {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.scroll-to-bottom-btn svg {
  width: 20px;
  height: 20px;
}

/* 音频播放指示器 */
.audio-indicator {
  position: fixed;
  bottom: 140px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--surface-color);
  padding: 0.75rem 1.5rem;
  border-radius: 24px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-color);
  animation: fadeIn 0.3s ease-out;
}

.waveform {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 24px;
}

.waveform span {
  width: 3px;
  height: 4px;
  background: var(--primary-color);
  border-radius: 2px;
  animation: waveform 0.5s ease-in-out infinite;
}

.waveform span:nth-child(2) {
  animation-delay: 0.1s;
}

.waveform span:nth-child(3) {
  animation-delay: 0.2s;
}

.waveform span:nth-child(4) {
  animation-delay: 0.3s;
}

.waveform span:nth-child(5) {
  animation-delay: 0.4s;
}

.audio-indicator span:last-child {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-header {
    padding: 0.75rem 1rem;
  }
  
  .logo h1 {
    font-size: 1rem;
  }
  
  .connection-status {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }
  
  .chat-messages {
    padding: 1rem;
  }
  
  .message {
    max-width: 90%;
  }
  
  .chat-footer {
    padding: 0.75rem 1rem;
  }
  
  .input-area {
    gap: 0.75rem;
  }
  
  .voice-btn {
    width: 56px;
    height: 56px;
  }
  
  .mic-icon {
    width: 24px;
    height: 24px;
  }
}
</style>
