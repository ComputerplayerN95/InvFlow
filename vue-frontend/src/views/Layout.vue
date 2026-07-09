<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="logo-container">
        <span v-if="!isCollapse" class="logo-text">InvFlow 进销存</span>
        <span v-else class="logo-text logo-small">IF</span>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        background-color="#1f2d3d"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-sub-menu index="2">
          <template #title>
            <el-icon><Box /></el-icon>
            <span>基础数据</span>
          </template>
          <el-menu-item index="/categories">商品类型</el-menu-item>
          <el-menu-item index="/warehouses">仓库管理</el-menu-item>
          <el-menu-item index="/suppliers">供应商管理</el-menu-item>
          <el-menu-item index="/customers">客户管理</el-menu-item>
          <el-menu-item index="/products">商品管理</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="3">
          <template #title>
            <el-icon><Tickets /></el-icon>
            <span>业务单据</span>
          </template>
          <el-menu-item index="/purchases">采购管理</el-menu-item>
          <el-menu-item index="/sales">销售管理</el-menu-item>
          <el-menu-item index="/transfers">调拨管理</el-menu-item>
          <el-menu-item index="/purchase-returns">采购退货</el-menu-item>
          <el-menu-item index="/sale-returns">销售退货</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="4">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>库存查询</span>
          </template>
          <el-menu-item index="/stock-total">库存总表</el-menu-item>
          <el-menu-item index="/stock-warehouse">仓库库存</el-menu-item>
          <el-menu-item index="/stock-monthly">月度结存</el-menu-item>
          <el-menu-item index="/stock-checks">盘点管理</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="5">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>报表中心</span>
          </template>
          <el-menu-item index="/reports">综合报表</el-menu-item>
        </el-sub-menu>
      </el-menu>
      <div class="collapse-btn" @click="isCollapse = !isCollapse">
        <el-icon><Fold v-if="!isCollapse" /><Expand v-else /></el-icon>
      </div>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta?.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <span class="header-time">{{ currentTime }}</span>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
    <ChatAssistant />
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Odometer, Box, Tickets, DataAnalysis, Document, Fold, Expand } from '@element-plus/icons-vue'
import ChatAssistant from '../components/ChatAssistant.vue'

const route = useRoute()
const isCollapse = ref(false)

const currentTime = ref('')
let timer = null

function updateTime() {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${h}:${m}:${s}`
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.layout-container { height: 100vh; }
.layout-aside {
  background-color: #1f2d3d;
  transition: width 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
  white-space: nowrap;
}
.logo-small { font-size: 20px; }
.layout-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 50px !important;
}
.header-time { color: #909399; font-size: 13px; }
.layout-main {
  background: #f0f2f5;
  padding: 16px;
  overflow-y: auto;
}
.el-menu { border-right: none; }
.collapse-btn {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bfcbd9;
  cursor: pointer;
  border-top: 1px solid rgba(255,255,255,0.1);
  transition: all 0.2s;
}
.collapse-btn:hover { color: #409EFF; background: rgba(64,158,255,0.1); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>