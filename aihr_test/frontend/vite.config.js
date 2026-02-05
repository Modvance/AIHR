import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Docker 环境下的文件监听配置
    watch: {
      usePolling: true,
      interval: 1000
    },
    proxy: {
      '/ws': {
        target: 'ws://backend:8000',
        ws: true
      }
    }
  }
})
