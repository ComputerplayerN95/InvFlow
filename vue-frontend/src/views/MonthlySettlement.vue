<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">月度结存管理</span>
          <div style="display:flex;gap:8px;align-items:center">
            <el-date-picker v-model="settleMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width:160px" />
            <el-input v-model="operator" placeholder="操作人" style="width:120px" />
            <el-button type="primary" @click="doSettle">执行结存</el-button>
            <el-button type="warning" @click="doAntiSettle">反结存</el-button>
          </div>
        </div>
      </template>

      <CrudTable
        :data="list"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="false"
        action-width="0"
      >
        <template #beginAmount="{ row }">{{ row.BeginAmount?.toFixed(2) }}</template>
        <template #inAmount="{ row }">{{ row.InAmount?.toFixed(2) }}</template>
        <template #outAmount="{ row }">{{ row.OutAmount?.toFixed(2) }}</template>
        <template #endAmount="{ row }">{{ row.EndAmount?.toFixed(2) }}</template>
      </CrudTable>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'

const list = ref([]); const loading = ref(false)
const settleMonth = ref(''); const operator = ref('系统')

const columns = [
  { prop: 'YearMonth', label: '月份', width: 100 },
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 150 },
  { prop: 'CategoryName', label: '类型', width: 100 },
  { prop: 'BeginQty', label: '期初数量', width: 100 },
  { label: '期初金额', width: 120, slot: 'beginAmount' },
  { prop: 'InQty', label: '入库数量', width: 100 },
  { label: '入库金额', width: 120, slot: 'inAmount' },
  { prop: 'OutQty', label: '出库数量', width: 100 },
  { label: '出库金额', width: 120, slot: 'outAmount' },
  { prop: 'EndQty', label: '期末数量', width: 100 },
  { label: '期末金额', width: 120, slot: 'endAmount' },
]

const loadData = async () => {
  loading.value = true
  const res = await stockApi.monthlyList()
  list.value = Array.isArray(res) ? res : (res.data || [])
  loading.value = false
}

const doSettle = async () => {
  if (!settleMonth.value) { ElMessage.warning('请选择月份'); return }
  await ElMessageBox.confirm(`确定执行 ${settleMonth.value} 月度结存？`, '确认', { type: 'success' })
  await stockApi.monthlySettle({ YearMonth: settleMonth.value, Operator: operator.value })
  ElMessage.success('月度结存完成'); loadData()
}

const doAntiSettle = async () => {
  if (!settleMonth.value) { ElMessage.warning('请选择月份'); return }
  await ElMessageBox.confirm(`确定执行 ${settleMonth.value} 反结存？`, '确认', { type: 'warning' })
  await stockApi.monthlyAntiSettle({ YearMonth: settleMonth.value })
  ElMessage.success('反结存完成'); loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
