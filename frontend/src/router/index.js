import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'upload', component: () => import('../views/Upload.vue') },
  { path: '/task/:id', name: 'task-detail', component: () => import('../views/TaskDetail.vue') },
  { path: '/tasks', name: 'tasks', component: () => import('../views/Tasks.vue') },
  { path: '/stats', name: 'stats', component: () => import('../views/Stats.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
