/**
 * 音频录制工具类
 * 使用 Web Audio API 捕获麦克风音频并转换为 PCM 格式
 */

export class AudioRecorder {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 16000 // ASR 需要 16kHz
    this.channelCount = options.channelCount || 1 // 单声道
    this.bufferSize = options.bufferSize || 4096
    
    this.audioContext = null
    this.mediaStream = null
    this.mediaStreamSource = null
    this.scriptProcessor = null
    this.isRecording = false
    
    this.onAudioData = options.onAudioData || null
    this.onError = options.onError || null
  }
  
  /**
   * 请求麦克风权限并初始化音频上下文
   */
  async init() {
    try {
      // 请求麦克风权限
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: this.channelCount,
          sampleRate: this.sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      // 创建音频上下文
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: this.sampleRate
      })
      
      // 创建媒体流源
      this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream)
      
      // 创建脚本处理器节点
      this.scriptProcessor = this.audioContext.createScriptProcessor(
        this.bufferSize,
        this.channelCount,
        this.channelCount
      )
      
      // 处理音频数据
      this.scriptProcessor.onaudioprocess = (event) => {
        if (!this.isRecording) return
        
        const inputBuffer = event.inputBuffer.getChannelData(0)
        
        // 重采样到目标采样率（如果需要）
        const resampledData = this.resample(inputBuffer, this.audioContext.sampleRate, this.sampleRate)
        
        // 转换为 16bit PCM
        const pcmData = this.floatTo16BitPCM(resampledData)
        
        if (this.onAudioData) {
          this.onAudioData(pcmData)
        }
      }
      
      return true
    } catch (error) {
      console.error('Failed to initialize audio recorder:', error)
      if (this.onError) {
        this.onError(error)
      }
      return false
    }
  }
  
  /**
   * 开始录音
   */
  start() {
    if (!this.audioContext || !this.scriptProcessor) {
      console.error('Audio recorder not initialized')
      return false
    }
    
    // 连接音频节点
    this.mediaStreamSource.connect(this.scriptProcessor)
    this.scriptProcessor.connect(this.audioContext.destination)
    
    this.isRecording = true
    console.log('Recording started')
    return true
  }
  
  /**
   * 停止录音
   */
  stop() {
    if (!this.isRecording) return
    
    this.isRecording = false
    
    // 断开音频节点
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect()
    }
    if (this.mediaStreamSource) {
      this.mediaStreamSource.disconnect()
    }
    
    console.log('Recording stopped')
  }
  
  /**
   * 释放资源
   */
  destroy() {
    this.stop()
    
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop())
      this.mediaStream = null
    }
    
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    
    this.scriptProcessor = null
    this.mediaStreamSource = null
  }
  
  /**
   * 重采样音频数据
   */
  resample(inputData, inputSampleRate, outputSampleRate) {
    if (inputSampleRate === outputSampleRate) {
      return inputData
    }
    
    const ratio = inputSampleRate / outputSampleRate
    const outputLength = Math.round(inputData.length / ratio)
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
   * 将浮点音频数据转换为 16bit PCM
   */
  floatTo16BitPCM(floatData) {
    const buffer = new ArrayBuffer(floatData.length * 2)
    const view = new DataView(buffer)
    
    for (let i = 0; i < floatData.length; i++) {
      // 限制在 [-1, 1] 范围内
      const sample = Math.max(-1, Math.min(1, floatData[i]))
      // 转换为 16bit 整数
      const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
      view.setInt16(i * 2, int16, true) // 小端序
    }
    
    return new Uint8Array(buffer)
  }
}
