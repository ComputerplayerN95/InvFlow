<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in cards" :key="card.title">
        <el-card shadow="hover" class="stat-card" :body-style="{ padding: '20px' }">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: card.color }">
              <span class="icon-text">{{ card.icon }}</span>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card>
          <template #header><span style="font-weight:600">各仓库库存分布</span></template>
          <div ref="warehouseChartRef" style="height:320px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span style="font-weight:600">商品类别占比</span></template>
          <div ref="categoryChartRef" style="height:320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 库存表格 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="24">
        <el-card>
          <template #header><span style="font-weight:600">库存总表概览</span></template>
          <CrudTable
            :data="totalStocks"
            :columns="stockColumns"
            :loading="stockLoading"
            :show-pagination="false"
            :show-index="true"
            action-width="0"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { productApi, warehouseApi, supplierApi, customerApi, stockApi } from '../api'
import CrudTable from '../components/CrudTable.vue'
import * as echarts from 'echarts'

const cards = ref([
  { title: '商品数量', value: 0, icon: '📦', color: 'linear-gradient(135deg, #409EFF, #337ecc)' },
  { title: '仓库数量', value: 0, icon: '🏭', color: 'linear-gradient(135deg, #67C23A, #529b2e)' },
  { title: '供应商数', value: 0, icon: '🚚', color: 'linear-gradient(135deg, #E6A23C, #b88230)' },
  { title: '客户数量', value: 0, icon: '👥', color: 'linear-gradient(135deg, #F56C6C, #c45656)' },
])

const warehouseStocks = ref([])
const totalStocks = ref([])
const catSummary = ref([])
const stockLoading = ref(false)
const warehouseChartRef = ref(null)
const categoryChartRef = ref(null)
let warehouseChart = null
let categoryChart = null

const stockColumns = [
  { prop: 'ProductName', label: '商品名称', minWidth: 150 },
  { prop: 'TotalQuantity', label: '总库存', width: 100 },
  { prop: 'AveragePrice', label: '均价(元)', width: 100 },
  { prop: 'LastPurchasePrice', label: '最后采购价', width: 120 },
]

let chartsInitialized = false

const initCharts = async () => {
  await nextTick()
  if (!warehouseChartRef.value || !categoryChartRef.value) return

  // 仓库库存柱状图
  warehouseChart = echarts.init(warehouseChartRef.value)
  const whStocks = Array.isArray(warehouseStocks.value) ? warehouseStocks.value : (warehouseStocks.value.data || [])
  const warehouseNames = [...new Set(whStocks.map(s => s.WarehouseName))]
  const whData = warehouseNames.map(name => ({
    name,
    value: whStocks.filter(s => s.WarehouseName === name).reduce((sum, s) => sum + (s.Quantity || 0), 0)
  }))

  warehouseChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: whData.map(d => d.name), axisLabel: { rotate: 0 } },
    yAxis: { type: 'value', name: '库存数量' },
    series: [{
      type: 'bar',
      data: whData.map(d => d.value),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: '#409EFF' }, { offset: 1, color: '#79bbff' }
      ]) },
      barMaxWidth: 50
    }],
    grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true }
  })

  // 类别占比饼图
  categoryChart = echarts.init(categoryChartRef.value)

  // 从 API 获取的类别统计数据
  const catData = (catSummary.value || []).map(c => ({
    name: c.CategoryName || c.category_name || '未分类',
    value: c.total_quantity || c.TotalQuantity || 0
  }))

  categoryChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['30%', '60%'],
      center: ['50%', '55%'],
      data: catData,
      label: { show: true, formatter: '{b}' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } }
    }]
  })

  chartsInitialized = true
}

const handleResize = () => {
  warehouseChart?.resize()
  categoryChart?.resize()
}

onMounted(async () => {
  try {
    const data = await Promise.all([
      productApi.list(), warehouseApi.list(), supplierApi.list(), customerApi.list(),
      stockApi.warehouse(), stockApi.total(), stockApi.summaryByCategory(),
    ])
    cards.value[0].value = (Array.isArray(data[0]) ? data[0] : (data[0].data || [])).length
    cards.value[1].value = (Array.isArray(data[1]) ? data[1] : (data[1].data || [])).length
    cards.value[2].value = (Array.isArray(data[2]) ? data[2] : (data[2].data || [])).length
    cards.value[3].value = (Array.isArray(data[3]) ? data[3] : (data[3].data || [])).length
    warehouseStocks.value = Array.isArray(data[4]) ? data[4].slice(0, 15) : (data[4].data || [])
    totalStocks.value = Array.isArray(data[5]) ? data[5] : (data[5].data || [])
    catSummary.value = Array.isArray(data[6]) ? data[6] : (data[6].data || [])

    await initCharts()
  } catch (e) { /* handled by interceptor */ }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  warehouseChart?.dispose()
  categoryChart?.dispose()
})
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.stat-card { cursor: pointer; transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-4px); }
.stat-content { display: flex; align-items: center; gap: 16px; }
.stat-icon {
  width: 56px; height: 56px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 24px; flex-shrink: 0;
}
.stat-value { font-size: 26px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>
