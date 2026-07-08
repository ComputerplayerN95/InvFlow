<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">销售管理</span>
          <div class="header-actions">
            <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:130px;margin-right:10px" @change="loadData">
              <el-option label="全部" value="" />
              <el-option label="草稿" value="草稿" />
              <el-option label="已出库" value="已出库" />
              <el-option label="已回退" value="已回退" />
            </el-select>
            <el-button type="primary" @click="openCreate">+ 新增销售单</el-button>
          </div>
        </div>
      </template>

      <CrudTable
        :data="list"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="true"
        action-width="320"
      >
        <template #status="{ row }">
          <StatusTag :status="row.Status" />
        </template>
        <template #amount="{ row }">
          {{ row.TotalAmount?.toFixed(2) }}
        </template>
        <template #action="{ row }">
          <el-button v-if="row.Status==='草稿'" size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="success" @click="handleOutStock(row)">出库</el-button>
          <el-button v-if="row.Status==='已出库'" size="small" type="warning" @click="handleRollback(row)">出库回退</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="danger" @click="handleDelete(row.SaleID)">删除</el-button>
          <el-button size="small" @click="drawerOpen(row.SaleID)">详情</el-button>
        </template>
      </CrudTable>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑销售单':'新增销售单'" width="900px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="单号" prop="SaleID">
              <el-input v-model="form.SaleID" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="客户" prop="CustomerID">
              <el-select v-model="form.CustomerID" placeholder="请选择" style="width:100%" :disabled="isEdit">
                <el-option v-for="c in customers" :key="c.CustomerID" :label="c.CustomerName" :value="c.CustomerID" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="仓库" prop="WarehouseID">
              <el-select v-model="form.WarehouseID" placeholder="请选择" style="width:100%" :disabled="isEdit">
                <el-option v-for="w in warehouses" :key="w.WarehouseID" :label="w.WarehouseName" :value="w.WarehouseID" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="制单人">
          <el-input v-model="form.Operator" style="width:200px" />
        </el-form-item>
      </el-form>

      <el-divider>
        <span style="font-size:13px;color:#909399">销售明细（共 {{ details.length }} 项）</span>
      </el-divider>
      <el-table :data="details" border size="small" max-height="300">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="商品" min-width="180">
          <template #default="{row}">
            <el-select v-model="row.ProductID" filterable placeholder="选择商品" style="width:100%">
              <el-option v-for="p in products" :key="p.ProductID" :label="p.ProductName" :value="p.ProductID" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="130">
          <template #default="{row}">
            <el-input-number v-model="row.Quantity" :min="0.01" :precision="2" size="small" controls-position="right" style="width:120px" @change="calcAmount(row)" />
          </template>
        </el-table-column>
        <el-table-column label="单价(元)" width="130">
          <template #default="{row}">
            <el-input-number v-model="row.UnitPrice" :min="0" :precision="2" size="small" controls-position="right" style="width:120px" @change="calcAmount(row)" />
          </template>
        </el-table-column>
        <el-table-column label="金额(元)" width="120">
          <template #default="{row}">{{ (row.Amount || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link @click="details.splice($index,1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:10px;display:flex;justify-content:space-between;align-items:center">
        <el-button size="small" @click="addDetail">+ 添加明细</el-button>
        <span style="font-weight:bold;font-size:15px">合计：{{ details.reduce((s, d) => s + (d.Amount || 0), 0).toFixed(2) }} 元</span>
      </div>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="销售单详情" size="700px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="单号">{{ currentOrder.SaleID }}</el-descriptions-item>
          <el-descriptions-item label="状态"><StatusTag :status="currentOrder.Status" /></el-descriptions-item>
          <el-descriptions-item label="客户">{{ currentOrder.CustomerName }}</el-descriptions-item>
          <el-descriptions-item label="仓库">{{ currentOrder.WarehouseName }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ currentOrder.OrderDate }}</el-descriptions-item>
          <el-descriptions-item label="总金额">{{ currentOrder.TotalAmount?.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="出库时间">{{ currentOrder.OutDate || '-' }}</el-descriptions-item>
          <el-descriptions-item label="出库人">{{ currentOrder.OutOperator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="回退时间">{{ currentOrder.RollbackDate || '-' }}</el-descriptions-item>
          <el-descriptions-item label="回退人">{{ currentOrder.RollbackOperator || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin:16px 0 8px">销售明细</h4>
        <el-table :data="currentOrder.Details || []" border size="small">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="ProductID" label="商品编号" width="120" />
          <el-table-column prop="Quantity" label="数量" width="80" />
          <el-table-column label="单价" width="100"><template #default="{row}">{{ row.UnitPrice?.toFixed(2) }}</template></el-table-column>
          <el-table-column label="金额" width="120"><template #default="{row}">{{ row.Amount?.toFixed(2) }}</template></el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { saleApi, customerApi, warehouseApi, productApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import StatusTag from '../components/StatusTag.vue'
import { genOrderId, genDetailId } from '../utils/id-generator.js'

const list = ref([])
const customers = ref([])
const warehouses = ref([])
const products = ref([])
const loading = ref(false)
const saving = ref(false)
const filterStatus = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ SaleID: '', CustomerID: '', WarehouseID: '', Operator: '系统' })
const details = ref([])
const drawerVisible = ref(false)
const currentOrder = ref(null)

const columns = [
  { prop: 'SaleID', label: '单号', width: 150 },
  { prop: 'CustomerName', label: '客户', width: 160 },
  { prop: 'WarehouseName', label: '仓库', width: 120 },
  { prop: 'Status', label: '状态', width: 100, slot: 'status' },
  { prop: 'TotalAmount', label: '总金额(元)', width: 120, slot: 'amount' },
  { prop: 'OrderDate', label: '日期', width: 160 },
  { prop: 'OutDate', label: '出库时间', width: 160 },
]

const formRules = {
  SaleID: [{ required: true, message: '请输入单号', trigger: 'blur' }],
  CustomerID: [{ required: true, message: '请选择客户', trigger: 'change' }],
  WarehouseID: [{ required: true, message: '请选择仓库', trigger: 'change' }],
}

const loadData = async () => {
  loading.value = true
  const params = filterStatus.value ? { status: filterStatus.value } : {}
  const res = await saleApi.list(params)
  list.value = res
  loading.value = false
}

const loadRefs = async () => {
  const [c, w, p] = await Promise.all([customerApi.list(), warehouseApi.list(), productApi.list()])
  customers.value = Array.isArray(c) ? c : (c.data || [])
  warehouses.value = Array.isArray(w) ? w : (w.data || [])
  products.value = Array.isArray(p) ? p : (p.data || [])
}

const calcAmount = (row) => { row.Amount = (row.Quantity || 0) * (row.UnitPrice || 0) }

const addDetail = () => {
  details.value.push({ SaleDetailID: '', ProductID: '', Quantity: 1, UnitPrice: 0, Amount: 0 })
}

const openCreate = async () => {
  isEdit.value = false
  form.value = { SaleID: genOrderId('SO'), CustomerID: '', WarehouseID: '', Operator: '系统' }
  details.value = []
  await loadRefs()
  dialogVisible.value = true
}

const openEdit = async (row) => {
  isEdit.value = true
  form.value = { SaleID: row.SaleID, CustomerID: row.CustomerID, WarehouseID: row.WarehouseID, Operator: row.Operator }
  await loadRefs()

  const res = await saleApi.get(row.SaleID)
  const order = res
  details.value = (order.Details || []).map(d => ({ ...d, Amount: d.Quantity * d.UnitPrice }))
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  if (details.value.length === 0) { ElMessage.warning('请添加销售明细'); return }

  for (const item of details.value) {
    if (!item.ProductID) { ElMessage.warning('请为每条明细选择商品'); return }
    if (!item.Quantity || item.Quantity <= 0) { ElMessage.warning('数量必须大于0'); return }
  }

  saving.value = true
  try {
    const d = details.value.map((item, idx) => ({
      SaleDetailID: item.SaleDetailID || genDetailId('SD', form.value.SaleID, idx + 1),
      ProductID: item.ProductID,
      Quantity: item.Quantity,
      UnitPrice: item.UnitPrice,
      Amount: item.Quantity * item.UnitPrice
    }))

    if (isEdit.value) {
      await saleApi.update(form.value.SaleID, { ...form.value, Details: d })
    } else {
      await saleApi.create({ ...form.value, Details: d })
    }

    dialogVisible.value = false
    ElMessage.success(isEdit.value ? '编辑成功' : '创建成功')
    loadData()
  } catch (e) {
    console.error('保存出错:', e)
  } finally {
    saving.value = false
  }
}

const handleOutStock = async (row) => {
  await ElMessageBox.confirm(`确定将 "${row.SaleID}" 从 ${row.WarehouseName} 整单出库？`, '出库确认', { type: 'success' })
  const res = await saleApi.outStock(row.SaleID, '系统')
  if (res.success === false) {
    ElMessage.warning(res.message)
    if (res.insufficient_items?.length) {
      const items = res.insufficient_items.map(i => `${i.ProductName}: 需要${i.NeedQty}, 库存${i.AvailableQty}, 差${i.DiffQty}`).join('\n')
      ElMessageBox.alert(items, '库存不足 - 请进行仓库调拨', { type: 'warning' })
    }
  } else {
    ElMessage.success('出库成功')
    loadData()
  }
}

const handleRollback = async (row) => {
  await ElMessageBox.confirm(`确定对 "${row.SaleID}" 执行出库回退？`, '回退确认', { type: 'warning' })
  await saleApi.rollback(row.SaleID, '系统')
  ElMessage.success('出库回退成功')
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该销售单？', '删除确认', { type: 'warning' })
  await saleApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

const drawerOpen = async (id) => {
  const res = await saleApi.get(id)
  currentOrder.value = res
  drawerVisible.value = true
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; align-items: center; }
</style>
