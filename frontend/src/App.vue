<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand">
        <div class="logo">风</div>
        <span class="title">金融文本智能风控审查系统</span>
      </div>
      <el-menu mode="horizontal" :default-active="$route.path" router class="menu">
        <el-menu-item index="/">
          <el-icon><Upload /></el-icon>
          <span>上传审查</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Document /></el-icon>
          <span>历史任务</span>
        </el-menu-item>
        <el-menu-item index="/stats">
          <el-icon><DataAnalysis /></el-icon>
          <span>统计看板</span>
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { Upload, Document, DataAnalysis } from '@element-plus/icons-vue'
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
}
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 40px;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
  padding: 0 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}
.logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}
.menu {
  border-bottom: none;
}
.main {
  padding: 24px;
}
</style>
