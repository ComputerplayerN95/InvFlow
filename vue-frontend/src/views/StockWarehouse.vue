<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">各仓库库存</span>
          <el-select v-model="filterWarehouse" placeholder="选择仓库" clearable @change="loadData" style="width:180px">
            <el-option v-for="w in warehouses" :key="w.WarehouseID" :label="w.WarehouseName" :value="w.WarehouseID" />
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
      </CrudTable>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockApi, warehouseApi } from '../api'
import CrudTable from '../components/CrudTable.vue'

const list = ref([]); const warehouses = ref([])
const loading = ref(false); const filterWarehouse = ref('')

const columns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 150 },
  { prop: 'WarehouseName', label: '仓库', width: 130 },
  { prop: 'Quantity', label: '库存数量', width: 120 },
  { prop: 'LastUpdated', label: '最后更新', width: 170 },
]

const loadData = async () => {
  loading.value = true
  const params = filterWarehouse.value ? { warehouse_id: filterWarehouse.value } : {}
  const [sRes, wRes] = await Promise.all([stockApi.warehouse(params), warehouseApi.list()])
  list.value = Array.isArray(sRes) ? sRes : (sRes.data || [])
  warehouses.value = Array.isArray(wRes) ? wRes : (wRes.data || [])
  loading.value = false
}
onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
