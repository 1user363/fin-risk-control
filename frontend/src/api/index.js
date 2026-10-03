import axios from 'axios'

// 统一 axios 实例：baseURL 走 /api（Vite 代理转发到后端）
const api = axios.create({
  baseURL: '/api',
  timeout: 180000, // 审查含 LLM 调用，超时设长
})

export default {
  // 上传文档 → 返回 { task_id, task_no, file_name }
  upload(file) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/upload', form)
  },
  // 触发 AI 审查流水线
  review(taskId) {
    return api.post(`/review/${taskId}`)
  },
  // 提交人工复核
  submitReview(taskId, payload) {
    return api.post(`/review/${taskId}/submit`, payload)
  },
  // 查询初审报告
  getReport(taskId) {
    return api.get(`/report/${taskId}`)
  },
  // 历史任务列表
  listTasks() {
    return api.get('/tasks')
  },
  // 风险统计
  getStats() {
    return api.get('/stats')
  },
}
