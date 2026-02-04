/**
 * WebSocket 连接管理器
 * 处理与后端的实时通信
 */

export class WebSocketManager {
  constructor(options = {}) {
    this.url = options.url || `ws://${window.location.hostname}:8000/ws/voice-chat`
    this.reconnectInterval = options.reconnectInterval || 3000
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5
    
    this.ws = null
    this.reconnectAttempts = 0
    this.isConnected = false
    this.sessionId = null
    
    // 事件回调
    this.onConnect = options.onConnect || null
    this.onDisconnect = options.onDisconnect || null
    this.onMessage = options.onMessage || null
    this.onError = options.onError || null
    
    // 消息处理器映射
    this.messageHandlers = new Map()
  }
  
  /**
   * 连接到 WebSocket 服务器
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)
        
        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.isConnected = true
          this.reconnectAttempts = 0
          
          if (this.onConnect) {
            this.onConnect()
          }
          
          resolve()
        }
        
        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.isConnected = false
          this.sessionId = null
          
          if (this.onDisconnect) {
            this.onDisconnect(event)
          }
          
          // 尝试重连
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++
            console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
            setTimeout(() => this.connect(), this.reconnectInterval)
          }
        }
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          if (this.onError) {
            this.onError(error)
          }
          reject(error)
        }
        
        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse message:', error)
          }
        }
        
      } catch (error) {
        console.error('Failed to connect:', error)
        reject(error)
      }
    })
  }
  
  /**
   * 处理接收到的消息
   */
  handleMessage(message) {
    const { type } = message
    
    // 处理会话创建
    if (type === 'session.created') {
      this.sessionId = message.session_id
      console.log('Session created:', this.sessionId)
    }
    
    // 调用注册的处理器
    const handler = this.messageHandlers.get(type)
    if (handler) {
      handler(message)
    }
    
    // 调用通用消息回调
    if (this.onMessage) {
      this.onMessage(message)
    }
  }
  
  /**
   * 注册消息处理器
   */
  on(messageType, handler) {
    this.messageHandlers.set(messageType, handler)
  }
  
  /**
   * 移除消息处理器
   */
  off(messageType) {
    this.messageHandlers.delete(messageType)
  }
  
  /**
   * 发送消息
   */
  send(message) {
    if (!this.isConnected || !this.ws) {
      console.error('WebSocket not connected')
      return false
    }
    
    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }
  
  /**
   * 发送音频数据
   * @param {Uint8Array} audioData - PCM 音频数据
   */
  sendAudio(audioData) {
    // 转换为 Base64
    const base64 = this.arrayBufferToBase64(audioData)
    return this.send({
      type: 'audio.input',
      data: base64
    })
  }
  
  /**
   * 结束音频输入
   */
  endAudio() {
    return this.send({
      type: 'audio.end'
    })
  }
  
  /**
   * 发送文本消息
   */
  sendText(text) {
    return this.send({
      type: 'text.input',
      text: text
    })
  }
  
  /**
   * 清空对话历史
   */
  clearHistory() {
    return this.send({
      type: 'clear.history'
    })
  }
  
  /**
   * 断开连接
   */
  disconnect() {
    this.maxReconnectAttempts = 0 // 防止重连
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
    this.isConnected = false
    this.sessionId = null
  }
  
  /**
   * ArrayBuffer 转 Base64
   */
  arrayBufferToBase64(buffer) {
    let binary = ''
    const bytes = new Uint8Array(buffer)
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }
  
  /**
   * Base64 转 Uint8Array
   */
  base64ToArrayBuffer(base64) {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    return bytes
  }
}
