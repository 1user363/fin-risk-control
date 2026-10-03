<template>
  <div class="upload-page">
    <el-card shadow="never">
      <h2>上传文档进行智能审查</h2>
      <p class="tip">支持 PDF / 图片（jpg/png/bmp/tif）格式，自动解析文本并完成「解析 → 抽取 → 三引擎风险识别 → 报告」全流程</p>

      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="onFileChange"
        :on-remove="onFileRemove"
        accept=".pdf,.jpg,.jpeg,.png,.bmp,.tif,.tiff"
        class="uploader"
      >
        <div class="upload-hint">
          <el-icon class="big-icon"><UploadFilled /></el-icon>
          <div class="hint-text">拖拽文件到此处，或 <em>点击选择</em></div>
          <div class="hint-sub">支持 PDF · JPG · PNG · BMP · TIF</div>
        </div>
      </el-upload>

      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!file"
        @click="submit"
        class="submit-btn"
      >
        <el-icon v-if="!loading" class="btn-icon"><VideoPlay /></el-icon>
        {{ loading ? '审查中，请稍候…' : '上传并审查' }}
      </el-button>
      <p v-if="file" class="selected">已选择：{{ file.name }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, VideoPlay } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const file = ref(null)
const loading = ref(false)

function onFileChange(f) {
  file.value = f.raw
}
function onFileRemove() {
  file.value = null
}

async function submit() {
  loading.value = true
  try {
    const up = await api.upload(file.value)
    const taskId = up.data.task_id
    ElMessage.success('上传成功，开始审查…')
    await api.review(taskId)
    ElMessage.success('审查完成')
    router.push(`/task/${taskId}`)
  } catch (e) {
    ElMessage.error('审查失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.upload-page {
  max-width: 720px;
  margin: 0 auto;
}
.tip {
  color: #909399;
  margin-bottom: 20px;
}
.uploader {
  margin-bottom: 20px;
}
.upload-hint {
  padding: 40px 0;
}
.big-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 12px;
}
.hint-text {
  font-size: 15px;
  color: #606266;
}
.hint-text em {
  color: #409eff;
  font-style: normal;
}
.hint-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 8px;
}
.submit-btn {
  width: 100%;
}
.btn-icon {
  margin-right: 6px;
}
.selected {
  color: #409eff;
  font-size: 13px;
  margin-top: 12px;
  text-align: center;
}
</style>
