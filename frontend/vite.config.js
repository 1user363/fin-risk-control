import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1', // 绑定 IPv4，避免 localhost 解析到 IPv6 导致无法访问
    // 开发代理：前端请求 /api/xxx → 转发到后端 127.0.0.1:8000
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
