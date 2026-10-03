<template>
  <div>
    <!-- 结论 -->
    <el-card shadow="never" class="mb">
      <div class="conclusion-row">
        <span class="label">初审结论：</span>
        <el-tag :type="conclusionType(report.conclusion)" size="large">{{ report.conclusion || '—' }}</el-tag>
        <span class="fname">{{ report.file_name }}</span>
        <el-button type="success" plain size="small" class="export-btn" @click="exportPdf">
          <el-icon><Download /></el-icon>&nbsp;导出 PDF
        </el-button>
      </div>
      <p class="summary">{{ report.risk_summary }}</p>
    </el-card>

    <!-- 实体信息 -->
    <el-card shadow="never" class="mb">
      <template #header><span class="card-title">实体信息</span></template>
      <el-descriptions v-if="report.entities" :column="3" border>
        <el-descriptions-item label="企业名称">{{ report.entities.company_name }}</el-descriptions-item>
        <el-descriptions-item label="统一社会信用代码">{{ report.entities.credit_code ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="法定代表人">{{ report.entities.legal_representative ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="授信金额">{{ report.entities.credit_amount ?? '—' }} 万元</el-descriptions-item>
        <el-descriptions-item label="币种">{{ report.entities.currency ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="授信期限">{{ report.entities.credit_term_months ?? '—' }} 个月</el-descriptions-item>
        <el-descriptions-item label="年化利率">{{ report.entities.interest_rate ?? '—' }}%</el-descriptions-item>
        <el-descriptions-item label="资产负债率">{{ report.entities.debt_ratio ?? '—' }}%</el-descriptions-item>
        <el-descriptions-item label="负债总额">{{ report.entities.total_liability ?? '—' }} 万元</el-descriptions-item>
        <el-descriptions-item label="应收账款">{{ report.entities.accounts_receivable ?? '—' }} 万元</el-descriptions-item>
        <el-descriptions-item label="对外担保">{{ report.entities.external_guarantee ?? '—' }} 万元</el-descriptions-item>
        <el-descriptions-item label="担保主体">{{ (report.entities.guarantors || []).join('、') || '—' }}</el-descriptions-item>
        <el-descriptions-item label="担保方式">{{ report.entities.guarantee_type ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="履约到期日">{{ report.entities.due_date ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="是否逾期">{{ overdueText(report.entities.has_overdue) }}</el-descriptions-item>
        <el-descriptions-item label="逾期详情">{{ report.entities.overdue_detail ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="涉诉情况">{{ report.entities.litigation ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="主营业务">{{ report.entities.main_business ?? '—' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="未抽取到实体信息" :image-size="60" />
    </el-card>

    <!-- 风险点 + 复核 -->
    <el-card shadow="never" class="mb">
      <template #header>
        <div class="risk-header">
          <span class="card-title">风险点（{{ risks.length }}）</span>
          <el-button type="primary" size="small" @click="openAddDialog">＋ 新增风险</el-button>
        </div>
      </template>

      <el-table :data="risks">
        <el-table-column label="类型" width="110">
          <template #default="{ row }"><el-tag>{{ row.risk_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="等级" width="160">
          <template #default="{ row, $index }">
            <el-tag :type="levelType(row.risk_level)" size="small" class="lv-tag">{{ row.risk_level }}</el-tag>
            <el-select :model-value="row.risk_level" size="small" @change="v => modifyLevel($index, v)" style="width: 70px">
              <el-option v-for="lv in ['高', '中', '低']" :key="lv" :label="lv" :value="lv" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="风险描述" show-overflow-tooltip />
        <el-table-column prop="evidence" label="原文依据" show-overflow-tooltip />
        <el-table-column prop="suggestion" label="整改建议" show-overflow-tooltip />
        <el-table-column label="来源" width="80">
          <template #default="{ row }">
            <el-tag :type="row.engine === 'rule' ? 'info' : 'warning'" size="small">
              {{ row.engine === 'rule' ? '规则' : '语义' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ $index }">
            <el-button type="danger" size="small" link @click="revoke($index)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="submit-row">
        <el-button type="primary" :loading="submitting" @click="submitReview">提交复核</el-button>
        <span class="hint">已记录 {{ actions.length }} 条复核动作</span>
      </div>
    </el-card>

    <!-- 综合建议 -->
    <el-card v-if="report.suggestions?.length" shadow="never">
      <template #header><span class="card-title">综合合规建议</span></template>
      <ul class="suggestions">
        <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
      </ul>
    </el-card>

    <!-- 新增风险对话框 -->
    <el-dialog v-model="addDialogVisible" title="新增风险点" width="540px">
      <el-form :model="newRisk" label-width="90px">
        <el-form-item label="违规类型">
          <el-select v-model="newRisk.risk_type" style="width: 100%">
            <el-option v-for="t in ['夸大收益', '保本承诺', '债务异常', '虚假披露']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="newRisk.risk_level" style="width: 100%">
            <el-option v-for="lv in ['高', '中', '低']" :key="lv" :label="lv" :value="lv" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="newRisk.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="原文依据"><el-input v-model="newRisk.evidence" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="整改建议"><el-input v-model="newRisk.suggestion" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAdd">确定新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const taskId = route.params.id

const report = ref({})
const risks = ref([])
const actions = ref([])
const submitting = ref(false)
const addDialogVisible = ref(false)
const newRisk = ref({ risk_type: '夸大收益', risk_level: '中', description: '', evidence: '', suggestion: '' })

function exportPdf() {
  window.open(`/api/report/${taskId}/export`, '_blank')
}
function conclusionType(c) {
  return { 通过: 'success', 需人工复核: 'warning', 不通过: 'danger' }[c] || 'info'
}
function levelType(lv) {
  return { 高: 'danger', 中: 'warning', 低: 'info' }[lv] || 'info'
}
function overdueText(v) {
  return v === null || v === undefined ? '未提及' : v ? '是' : '否'
}

function modifyLevel(index, newLevel) {
  actions.value.push({ action: 'modify', risk_index: index, field_name: 'risk_level', new_value: newLevel })
  risks.value[index].risk_level = newLevel
}
function revoke(index) {
  actions.value.push({ action: 'revoke', risk_index: index })
  risks.value.splice(index, 1)
}
function openAddDialog() {
  addDialogVisible.value = true
}
function confirmAdd() {
  const nr = { ...newRisk.value, engine: 'semantic' }
  actions.value.push({ action: 'add', new_risk: nr })
  risks.value.push(nr)
  addDialogVisible.value = false
  newRisk.value = { risk_type: '夸大收益', risk_level: '中', description: '', evidence: '', suggestion: '' }
}
async function submitReview() {
  if (actions.value.length === 0) {
    ElMessage.warning('没有需要提交的复核动作')
    return
  }
  submitting.value = true
  try {
    const res = await api.submitReview(taskId, { reviewer: '风控员', actions: actions.value })
    ElMessage.success('复核已提交，终审结论：' + res.data.final_conclusion)
    actions.value = []
  } catch (e) {
    ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const res = await api.getReport(taskId)
  report.value = res.data.report || res.data
  risks.value = report.value.risks || []
})
</script>

<style scoped>
.mb {
  margin-bottom: 16px;
}
.card-title {
  font-weight: 600;
}
.conclusion-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.label {
  color: #606266;
}
.fname {
  color: #909399;
  margin-left: 8px;
}
.export-btn {
  margin-left: auto;
}
.summary {
  color: #606266;
  margin-top: 12px;
}
.risk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.lv-tag {
  margin-right: 6px;
}
.submit-row {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.hint {
  color: #909399;
  font-size: 13px;
}
.suggestions {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}
.suggestions li {
  margin-bottom: 8px;
}
</style>
