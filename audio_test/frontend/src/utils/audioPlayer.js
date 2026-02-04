/**
 * 音频播放工具类
 * 播放 PCM 格式的音频数据
 */

export class AudioPlayer {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 24000 // TTS 输出 24kHz
    this.channelCount = options.channelCount || 1 // 单声道
    
    this.audioContext = null
    this.audioQueue = [] // 音频数据队列
    this.isPlaying = false
    this.currentSource = null
    this.nextPlayTime = 0
    
    this.onPlayStart = options.onPlayStart || null
    this.onPlayEnd = options.onPlayEnd || null
    this.onError = options.onError || null
  }
  
  /**
   * 初始化音频上下文
   */
  async init() {
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sampleRate
      })
      
      // 如果上下文被挂起，恢复它
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }
      
      return true
    } catch (error) {
      console.error('Failed to initialize audio player:', error)
      if (this.onError) {
        this.onError(error)
      }
      return false
    }
  }
  
  /**
   * 确保音频上下文正在运行
   */
  async ensureAudioContext() {
    if (!this.audioContext) {
      await this.init()
    }
    
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }
  }
  
  /**
   * 添加 PCM 音频数据到播放队列
   * @param {Uint8Array} pcmData - 16bit PCM 音频数据
   */
  async addPCMData(pcmData) {
    await this.ensureAudioContext()
    
    // 转换 PCM 数据为 AudioBuffer
    const audioBuffer = this.pcmToAudioBuffer(pcmData)
    
    // 添加到队列
    this.audioQueue.push(audioBuffer)
    
    // 如果没有在播放，开始播放
    if (!this.isPlaying) {
      this.playNext()
    }
  }
  
  /**
   * 将 16bit PCM 数据转换为 AudioBuffer
   */
  pcmToAudioBuffer(pcmData) {
    // PCM 是 16bit，所以每个样本 2 字节
    const numSamples = pcmData.length / 2
    const audioBuffer = this.audioContext.createBuffer(
      this.channelCount,
      numSamples,
      this.sampleRate
    )
    
    const channelData = audioBuffer.getChannelData(0)
    const dataView = new DataView(pcmData.buffer, pcmData.byteOffset, pcmData.byteLength)
    
    for (let i = 0; i < numSamples; i++) {
      // 读取 16bit 小端序整数
      const int16 = dataView.getInt16(i * 2, true)
      // 转换为 [-1, 1] 范围的浮点数
      channelData[i] = int16 / (int16 < 0 ? 0x8000 : 0x7FFF)
    }
    
    return audioBuffer
  }
  
  /**
   * 播放队列中的下一个音频
   */
  playNext() {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false
      if (this.onPlayEnd) {
        this.onPlayEnd()
      }
      return
    }
    
    this.isPlaying = true
    
    if (!this.isPlaying && this.onPlayStart) {
      this.onPlayStart()
    }
    
    const audioBuffer = this.audioQueue.shift()
    
    // 创建音频源
    const source = this.audioContext.createBufferSource()
    source.buffer = audioBuffer
    source.connect(this.audioContext.destination)
    
    // 计算播放时间（无缝连接）
    const currentTime = this.audioContext.currentTime
    const startTime = Math.max(currentTime, this.nextPlayTime)
    
    source.start(startTime)
    this.nextPlayTime = startTime + audioBuffer.duration
    
    source.onended = () => {
      this.playNext()
    }
    
    this.currentSource = source
  }
  
  /**
   * 停止播放并清空队列
   */
  stop() {
    this.audioQueue = []
    
    if (this.currentSource) {
      try {
        this.currentSource.stop()
      } catch (e) {
        // 忽略已经停止的源
      }
      this.currentSource = null
    }
    
    this.isPlaying = false
    this.nextPlayTime = 0
    
    if (this.onPlayEnd) {
      this.onPlayEnd()
    }
  }
  
  /**
   * 暂停播放
   */
  async pause() {
    if (this.audioContext && this.audioContext.state === 'running') {
      await this.audioContext.suspend()
    }
  }
  
  /**
   * 恢复播放
   */
  async resume() {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }
  }
  
  /**
   * 释放资源
   */
  destroy() {
    this.stop()
    
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
  }
  
  /**
   * 获取当前是否正在播放
   */
  get playing() {
    return this.isPlaying
  }
  
  /**
   * 获取队列中待播放的音频数量
   */
  get queueLength() {
    return this.audioQueue.length
  }
}
