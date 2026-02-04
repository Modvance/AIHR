/**
 * 音频录制工具
 * 使用 Web Audio API 录制音频并转换为 PCM 格式
 */

export class AudioRecorder {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 16000
    this.onAudioData = options.onAudioData || (() => {})
    
    this.audioContext = null
    this.mediaStream = null
    this.mediaStreamSource = null
    this.scriptProcessor = null
    this.isRecording = false
  }

  /**
   * 开始录音
   */
  async start() {
    if (this.isRecording) {
      console.warn('Already recording')
      return
    }

    try {
      // 请求麦克风权限
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: this.sampleRate,
          echoCancellation: true,
          noiseSuppression: true
        }
      })

      // 创建音频上下文
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sampleRate
      })

      // 创建媒体流源
      this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream)

      // 创建脚本处理器（用于获取原始音频数据）
      const bufferSize = 4096
      this.scriptProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1)

      this.scriptProcessor.onaudioprocess = (event) => {
        if (!this.isRecording) return

        const inputData = event.inputBuffer.getChannelData(0)
        
        // 重采样到目标采样率（如果需要）
        const resampledData = this._resample(inputData, this.audioContext.sampleRate, this.sampleRate)
        
        // 转换为 16-bit PCM
        const pcmData = this._floatTo16BitPCM(resampledData)
        
        this.onAudioData(pcmData)
      }

      // 连接节点
      this.mediaStreamSource.connect(this.scriptProcessor)
      this.scriptProcessor.connect(this.audioContext.destination)

      this.isRecording = true
      console.log('Recording started')
    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }

  /**
   * 停止录音
   */
  stop() {
    if (!this.isRecording) {
      return
    }

    this.isRecording = false

    // 断开节点
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect()
      this.scriptProcessor = null
    }

    if (this.mediaStreamSource) {
      this.mediaStreamSource.disconnect()
      this.mediaStreamSource = null
    }

    // 停止媒体流
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop())
      this.mediaStream = null
    }

    // 关闭音频上下文
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }

    console.log('Recording stopped')
  }

  /**
   * 重采样音频数据
   */
  _resample(inputData, inputSampleRate, outputSampleRate) {
    if (inputSampleRate === outputSampleRate) {
      return inputData
    }

    const ratio = inputSampleRate / outputSampleRate
    const outputLength = Math.ceil(inputData.length / ratio)
    const outputData = new Float32Array(outputLength)

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio
      const srcIndexFloor = Math.floor(srcIndex)
      const srcIndexCeil = Math.min(srcIndexFloor + 1, inputData.length - 1)
      const fraction = srcIndex - srcIndexFloor
      
      outputData[i] = inputData[srcIndexFloor] * (1 - fraction) + inputData[srcIndexCeil] * fraction
    }

    return outputData
  }

  /**
   * 浮点数转 16-bit PCM
   */
  _floatTo16BitPCM(floatData) {
    const buffer = new ArrayBuffer(floatData.length * 2)
    const view = new DataView(buffer)

    for (let i = 0; i < floatData.length; i++) {
      // 限制在 -1 到 1 之间
      const sample = Math.max(-1, Math.min(1, floatData[i]))
      // 转换为 16-bit 整数
      view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
    }

    return buffer
  }

  /**
   * 检查是否支持录音
   */
  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  }
}
