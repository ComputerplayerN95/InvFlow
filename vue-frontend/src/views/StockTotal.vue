<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">库存总表</span>
          <el-select v-model="filterCategory" placeholder="按类别筛选" clearable @change="loadData" style="width:180px">
            <el-option v-for="c in categories" :key="c.CategoryID" :label="c.CategoryName" :value="c.CategoryID" />
          </el-select>
        </div>
      </template>

      <CrudTable
        :data="list"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="true"
        action-width="0"
      >
        <template #avgPrice="{ row }">{{ row.AveragePrice?.toFixed(2) || '0.00' }}</template>
        <template #totalValue="{ row }">{{ ((row.TotalQuantity || 0) * (row.AveragePrice || 0)).toFixed(2) }}</template>
        <template #lastPrice="{ row }">{{ row.LastPurchasePrice?.toFixed(2) || '0.00' }}</template>
      </CrudTable>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockApi, categoryApi } from '../api'
import CrudTable from '../components/CrudTable.vue'

const list = ref([]); const categories = ref([])
const loading = ref(false); const filterCategory = ref('')

const columns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 150 },
  { prop: 'TotalQuantity', label: '总库存数量', width: 120 },
  { label: '进货均价(元)', width: 120, slot: 'avgPrice' },
  { label: '总金额(元)', width: 140, slot: 'totalValue' },
  { label: '最后采购价(元)', width: 130, slot: 'lastPrice' },
  { prop: 'LastUpdated', label: '最后更新', width: 170 },
]

const loadData = async () => {
  loading.value = true
  const params = filterCategory.value ? { category_id: filterCategory.value } : {}
  const [sRes, cRes] = await Promise.all([stockApi.total(params), categoryApi.list()])
  list.value = Array.isArray(sRes) ? sRes : (sRes.data || [])
  categories.value = Array.isArray(cRes) ? cRes : (cRes.data || [])
  loading.value = false
}
onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
