<template>
  <div>
    <h2>风险数据统计</h2>

    <!-- 三个核心指标卡片 -->
    <el-row :gutter="20" class="cards">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="num">{{ stats.total_tasks ?? '-' }}</div>
          <div class="label">审查任务总数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="num danger">{{ stats.total_risks ?? '-' }}</div>
          <div class="label">风险点总数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="num danger">{{ stats.high_risks ?? '-' }}</div>
          <div class="label">高风险点数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表 -->
    <el-row :gutter="20" class="charts">
      <el-col :span="12">
        <el-card shadow="never">
          <div ref="typeChart" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <div ref="levelChart" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const stats = ref({})
const typeChart = ref(null)
const levelChart = ref(null)

onMounted(async () => {
  const res = await api.getStats()
  stats.value = res.data
  await nextTick()
  renderTypeChart()
  renderLevelChart()
})

function renderTypeChart() {
  const chart = echarts.init(typeChart.value)
  chart.setOption({
    title: { text: '风险类型分布', left: 'center', textStyle: { fontSize: 15 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} 个 ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '55%'],
      label: { formatter: '{b}\n{c}' },
      data: stats.value.risk_types || [],
    }],
  })
}

function renderLevelChart() {
  const chart = echarts.init(levelChart.value)
  chart.setOption({
    title: { text: '风险等级分布', left: 'center', textStyle: { fontSize: 15 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: (stats.value.risk_levels || []).map(d => d.name) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'bar',
      barWidth: '45%',
      data: (stats.value.risk_levels || []).map(d => ({
        value: d.value,
        itemStyle: { color: { 高: '#f56c6c', 中: '#e6a23c', 低: '#909399' }[d.name] || '#409eff' },
      })),
      label: { show: true, position: 'top' },
    }],
  })
}
</script>

<style scoped>
.cards {
  margin-bottom: 20px;
}
.num {
  font-size: 36px;
  font-weight: 600;
  color: #303133;
}
.num.danger {
  color: #f56c6c;
}
.label {
  color: #909399;
  margin-top: 8px;
}
.charts {
  margin-top: 20px;
}
.chart {
  height: 320px;
}
</style>
