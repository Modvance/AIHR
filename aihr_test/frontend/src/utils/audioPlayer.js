/**
 * 音频播放工具
 * 使用 Web Audio API 播放 PCM 音频数据
 */

export class AudioPlayer {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 24000
    this.audioContext = null
    this.audioQueue = []
    this.isPlaying = false
    this.nextPlayTime = 0
    this.currentSource = null
  }

  /**
   * 初始化音频上下文
   */
  async initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sampleRate
      })
    }

    // 确保音频上下文处于运行状态
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }
  }

  /**
   * 播放 PCM 音频数据
   */
  async play(pcmData) {
    await this.initialize()

    // 将 PCM 数据添加到队列
    this.audioQueue.push(pcmData)

    // 如果没有正在播放，开始播放
    if (!this.isPlaying) {
      this._playNext()
    }
  }

  /**
   * 播放队列中的下一个音频
   */
  _playNext() {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false
      return
    }

    this.isPlaying = true
    const pcmData = this.audioQueue.shift()

    try {
      // 将 PCM 数据转换为 AudioBuffer
      const audioBuffer = this._pcmToAudioBuffer(pcmData)

      // 创建音频源
      const source = this.audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(this.audioContext.destination)

      // 计算播放时间
      const currentTime = this.audioContext.currentTime
      if (this.nextPlayTime < currentTime) {
        this.nextPlayTime = currentTime
      }

      // 开始播放
      source.start(this.nextPlayTime)
      
      // 更新下一个播放时间
      this.nextPlayTime += audioBuffer.duration

      // 播放结束后播放下一个
      source.onended = () => {
        this._playNext()
      }

      this.currentSource = source
    } catch (error) {
      console.error('Failed to play audio:', error)
      this._playNext()
    }
  }

  /**
   * PCM 数据转换为 AudioBuffer
   */
  _pcmToAudioBuffer(pcmData) {
    // pcmData 是 ArrayBuffer，包含 16-bit PCM 数据
    const int16Array = new Int16Array(pcmData)
    const float32Array = new Float32Array(int16Array.length)

    // 转换为浮点数
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0
    }

    // 创建 AudioBuffer
    const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, this.sampleRate)
    audioBuffer.getChannelData(0).set(float32Array)

    return audioBuffer
  }

  /**
   * 停止播放
   */
  stop() {
    // 清空队列
    this.audioQueue = []
    
    // 停止当前正在播放的音频
    if (this.currentSource) {
      try {
        this.currentSource.stop()
      } catch (e) {
        // 忽略已停止的错误
      }
      this.currentSource = null
    }

    this.isPlaying = false
    this.nextPlayTime = 0
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
   * 关闭音频上下文
   */
  close() {
    this.stop()
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
  }

  /**
   * 检查是否支持音频播放
   */
  static isSupported() {
    return !!(window.AudioContext || window.webkitAudioContext)
  }
}
