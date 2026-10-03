<template>
  <el-card shadow="never">
    <div class="toolbar">
      <h2>历史任务</h2>
      <div class="filters">
        <el-input
          v-model="search"
          placeholder="搜索文件名 / 任务编号"
          clearable
          style="width: 240px"
          :prefix-icon="Search"
        />
        <el-select v-model="statusFilter" placeholder="状态" style="width: 130px">
          <el-option label="全部" value="" />
          <el-option label="已完成" value="done" />
          <el-option label="处理中" value="pending" />
        </el-select>
      </div>
    </div>

    <el-table :data="pagedTasks" v-loading="loading" @row-click="goDetail" style="cursor: pointer">
      <el-table-column prop="task_no" label="任务编号" width="180" />
      <el-table-column prop="file_name" label="文件名" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'done' ? 'success' : 'info'" size="small">
            {{ row.status === 'done' ? '已完成' : row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="conclusion" label="结论" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.conclusion" :type="conclusionType(row.conclusion)" size="small">
            {{ row.conclusion }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filteredTasks.length"
        layout="total, prev, pager, next"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 10

const filteredTasks = computed(() => {
  const kw = search.value.toLowerCase()
  return tasks.value.filter(t => {
    const matchKw = !kw || t.file_name.toLowerCase().includes(kw) || t.task_no.toLowerCase().includes(kw)
    const matchStatus = !statusFilter.value || t.status === statusFilter.value
    return matchKw && matchStatus
  })
})
const pagedTasks = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredTasks.value.slice(start, start + pageSize)
})

function conclusionType(c) {
  return { 通过: 'success', 需人工复核: 'warning', 不通过: 'danger' }[c] || 'info'
}
function goDetail(row) {
  router.push(`/task/${row.id}`)
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await api.listTasks()
    tasks.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar h2 {
  margin: 0;
}
.filters {
  display: flex;
  gap: 12px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
