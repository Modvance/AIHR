/**
 * WebSocket 管理器
 * 用于与后端建立实时通信
 */

export class WebSocketManager {
  constructor(url) {
    this.url = url
    this.ws = null
    this.handlers = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.isConnecting = false
  }

  /**
   * 连接到 WebSocket 服务器
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (this.isConnecting) {
        reject(new Error('Already connecting'))
        return
      }

      this.isConnecting = true

      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.isConnecting = false
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.isConnecting = false
          this._handleClose()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          reject(error)
        }

        this.ws.onmessage = (event) => {
          this._handleMessage(event)
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 注册消息处理器
   */
  on(type, handler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, [])
    }
    this.handlers.get(type).push(handler)
  }

  /**
   * 移除消息处理器
   */
  off(type, handler) {
    if (this.handlers.has(type)) {
      const handlers = this.handlers.get(type)
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 发送 JSON 消息
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected')
    }
  }

  /**
   * 发送音频数据
   */
  sendAudio(audioData) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const base64 = this._arrayBufferToBase64(audioData)
      this.send({
        type: 'audio.input',
        data: base64
      })
    }
  }

  /**
   * 结束音频输入
   */
  endAudio() {
    this.send({ type: 'audio.end' })
  }

  /**
   * 发送文本消息
   */
  sendText(text) {
    this.send({
      type: 'text.input',
      text: text
    })
  }

  /**
   * 开始面试
   */
  startInterview(topic, position = '', resume = '') {
    this.send({
      type: 'interview.start',
      topic: topic,
      position: position,
      resume: resume
    })
  }

  /**
   * 重置面试
   */
  resetInterview() {
    this.send({ type: 'interview.reset' })
  }

  /**
   * 处理接收到的消息
   */
  _handleMessage(event) {
    try {
      const data = JSON.parse(event.data)
      const type = data.type

      if (this.handlers.has(type)) {
        this.handlers.get(type).forEach(handler => handler(data))
      }

      // 通用消息处理器
      if (this.handlers.has('*')) {
        this.handlers.get('*').forEach(handler => handler(data))
      }
    } catch (error) {
      console.error('Failed to parse message:', error)
    }
  }

  /**
   * 处理连接关闭
   */
  _handleClose() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
      setTimeout(() => {
        this.connect().catch(console.error)
      }, this.reconnectDelay * this.reconnectAttempts)
    }
  }

  /**
   * ArrayBuffer 转 Base64
   */
  _arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }

  /**
   * Base64 转 ArrayBuffer
   */
  static base64ToArrayBuffer(base64) {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    return bytes.buffer
  }

  /**
   * 获取连接状态
   */
  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}
