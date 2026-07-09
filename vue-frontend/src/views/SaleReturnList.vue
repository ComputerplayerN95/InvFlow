<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">销售退货管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openCreate">+ 新增退货单</el-button>
          </div>
        </div>
      </template>

      <CrudTable
        :data="list"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="true"
        action-width="300"
      >
        <template #status="{ row }">
          <StatusTag :status="row.Status" />
        </template>
        <template #action="{ row }">
          <el-button v-if="row.Status==='草稿'" size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="success" @click="handleExecute(row)">执行退货</el-button>
          <el-button v-if="row.Status==='已退货'" size="small" type="warning" @click="handleRollback(row)">回退</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="danger" @click="handleDelete(row.ReturnID)">删除</el-button>
          <el-button size="small" @click="drawerOpen(row.ReturnID)">详情</el-button>
        </template>
      </CrudTable>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑退货单':'新增退货单'" width="900px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="退货单号" prop="ReturnID">
              <el-input v-model="form.ReturnID" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="原销售单" prop="SaleID">
              <el-select v-model="form.SaleID" filterable placeholder="选择销售单" style="width:100%" :disabled="isEdit" @change="onSaleChange">
                <el-option v-for="so in saleOrders" :key="so.SaleID" :label="`${so.SaleID} - ${so.CustomerName}`" :value="so.SaleID" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="客户">
              <el-input :model-value="customerName" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="仓库">
              <el-input :model-value="warehouseName" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="退货日期">
              <el-date-picker v-model="form.ReturnDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="操作人">
              <el-input v-model="form.Operator" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.Remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <el-divider>
        <span style="font-size:13px;color:#909399">退货明细（共 {{ details.length }} 项）</span>
      </el-divider>
      <el-table :data="details" border size="small" max-height="350">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="ProductID" label="商品编号" width="110" />
        <el-table-column prop="ProductName" label="商品名称" width="160" />
        <el-table-column label="原数量" width="80">
          <template #default="{row}">{{ row.OrigQuantity }}</template>
        </el-table-column>
        <el-table-column label="退货数量" width="120">
          <template #default="{row}">
            <el-input-number v-model="row.Quantity" :min="0" :max="row.OrigQuantity || 999" :precision="0" size="small" controls-position="right" style="width:100px" @change="() => calcAmount(row)" />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100">
          <template #default="{row}">
            <el-input-number v-model="row.UnitPrice" :min="0" :precision="2" size="small" controls-position="right" :disabled="true" style="width:90px" />
          </template>
        </el-table-column>
        <el-table-column label="金额" width="110">
          <template #default="{row}">{{ (row.Amount || 0).toFixed(2) }}</template>
        </el-table-column>
      </el-table>

      <div style="text-align:right;margin-top:8px;font-size:14px;color:#606266">
        总金额：<span style="font-weight:700;color:#E6A23C">{{ totalAmount.toFixed(2) }}</span>
      </div>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="退货单详情" size="600px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="退货单号">{{ currentOrder.ReturnID }}</el-descriptions-item>
          <el-descriptions-item label="状态"><StatusTag :status="currentOrder.Status" /></el-descriptions-item>
          <el-descriptions-item label="原销售单">{{ currentOrder.SaleID }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ currentOrder.CustomerName }}</el-descriptions-item>
          <el-descriptions-item label="仓库">{{ currentOrder.WarehouseName }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ currentOrder.ReturnDate }}</el-descriptions-item>
          <el-descriptions-item label="操作人">{{ currentOrder.Operator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="退货总金额">{{ currentOrder.TotalAmount?.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ currentOrder.Remark || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin:16px 0 8px">退货明细</h4>
        <el-table :data="currentOrder.Details || []" border size="small">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="ProductID" label="商品" width="120" />
          <el-table-column prop="Quantity" label="数量" width="80" />
          <el-table-column prop="UnitPrice" label="单价" width="100" />
          <el-table-column prop="Amount" label="金额" width="100" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { saleReturnApi, saleApi, customerApi, warehouseApi, productApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import StatusTag from '../components/StatusTag.vue'
import { genOrderId, genDetailId } from '../utils/id-generator.js'

const list = ref([])
const saleOrders = ref([])
const customers = ref([])
const warehouses = ref([])
const products = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ ReturnID: '', SaleID: '', CustomerID: '', WarehouseID: '', ReturnDate: '', Operator: '系统', Remark: '' })
const details = ref([])
const drawerVisible = ref(false)
const currentOrder = ref(null)

const customerName = computed(() => {
  if (!form.value.CustomerID) return ''
  const c = customers.value.find(x => x.CustomerID === form.value.CustomerID)
  return c ? c.CustomerName : ''
})

const warehouseName = computed(() => {
  if (!form.value.WarehouseID) return ''
  const w = warehouses.value.find(x => x.WarehouseID === form.value.WarehouseID)
  return w ? w.WarehouseName : ''
})

const totalAmount = computed(() => {
  return details.value.reduce((sum, d) => sum + (d.Amount || 0), 0)
})

const columns = [
  { prop: 'ReturnID', label: '退货单号', width: 150 },
  { prop: 'SaleID', label: '原销售单', width: 140 },
  { prop: 'CustomerName', label: '客户', width: 140 },
  { prop: 'WarehouseName', label: '仓库', width: 120 },
  { prop: 'Status', label: '状态', width: 100, slot: 'status' },
  { prop: 'TotalAmount', label: '总金额', width: 120 },
  { prop: 'ReturnDate', label: '日期', width: 160 },
]

const formRules = {
  ReturnID: [{ required: true, message: '请输入退货单号', trigger: 'blur' }],
  SaleID: [{ required: true, message: '请选择原销售单', trigger: 'change' }],
}

const loadData = async () => {
  loading.value = true
  const res = await saleReturnApi.list()
  list.value = res
  loading.value = false
}

const loadRefs = async () => {
  const [s, c, w, pr] = await Promise.all([
    saleApi.list(), customerApi.list(), warehouseApi.list(), productApi.list()
  ])
  saleOrders.value = Array.isArray(s) ? s : (s.data || [])
  customers.value = Array.isArray(c) ? c : (c.data || [])
  warehouses.value = Array.isArray(w) ? w : (w.data || [])
  products.value = Array.isArray(pr) ? pr : (pr.data || [])
}

const calcAmount = (row) => {
  row.Amount = (row.Quantity || 0) * (row.UnitPrice || 0)
}

const onSaleChange = async (saleId) => {
  if (!saleId) return
  try {
    const so = await saleApi.get(saleId)
    form.value.CustomerID = so.CustomerID
    form.value.WarehouseID = so.WarehouseID
    details.value = (so.Details || []).map(d => {
      const prod = products.value.find(p => p.ProductID === d.ProductID)
      return {
        ReturnDetailID: '',
        SaleDetailID: d.SaleDetailID,
        ProductID: d.ProductID,
        ProductName: prod ? prod.ProductName : d.ProductID,
        OrigQuantity: d.Quantity,
        Quantity: 0,
        UnitPrice: d.UnitPrice,
        Amount: 0
      }
    })
  } catch(e) {
    form.value.CustomerID = ''
    form.value.WarehouseID = ''
    details.value = []
  }
}

const openCreate = async () => {
  isEdit.value = false
  form.value = { ReturnID: genOrderId('SR'), SaleID: '', CustomerID: '', WarehouseID: '', ReturnDate: new Date().toISOString().slice(0,19), Operator: '系统', Remark: '' }
  details.value = []
  await loadRefs()
  dialogVisible.value = true
}

const openEdit = async (row) => {
  isEdit.value = true
  form.value = {
    ReturnID: row.ReturnID, SaleID: row.SaleID,
    CustomerID: row.CustomerID, WarehouseID: row.WarehouseID,
    ReturnDate: row.ReturnDate, Operator: row.Operator, Remark: row.Remark
  }
  await loadRefs()
  await onSaleChange(row.SaleID)
  const res = await saleReturnApi.get(row.ReturnID)
  const order = res
  if (order.Details) {
    order.Details.forEach(d => {
      const idx = details.value.findIndex(x => x.SaleDetailID === d.SaleDetailID)
      if (idx >= 0) {
        details.value[idx].Quantity = d.Quantity
        details.value[idx].UnitPrice = d.UnitPrice
        details.value[idx].Amount = d.Amount
        details.value[idx].ReturnDetailID = d.ReturnDetailID
      }
    })
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    if (details.value.length === 0) { ElMessage.warning('请选择原销售单'); return }
    const validDetails = details.value.filter(d => (d.Quantity || 0) > 0)
    if (validDetails.length === 0) { ElMessage.warning('请填写退货数量'); return }
    saving.value = true
    try {
      const d = validDetails.map((item, idx) => ({
        ReturnDetailID: item.ReturnDetailID || genDetailId('SRD', form.value.ReturnID, idx + 1),
        SaleDetailID: item.SaleDetailID,
        ProductID: item.ProductID,
        Quantity: item.Quantity,
        UnitPrice: item.UnitPrice || 0,
        Amount: (item.Quantity || 0) * (item.UnitPrice || 0)
      }))
      if (isEdit.value) {
        await saleReturnApi.update(form.value.ReturnID, { ...form.value, Details: d })
      } else {
        await saleReturnApi.create({ ...form.value, Details: d })
      }
      dialogVisible.value = false
      ElMessage.success(isEdit.value ? '编辑成功' : '创建成功')
      loadData()
    } catch (e) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const handleExecute = async (row) => {
  await ElMessageBox.confirm(`确定执行退货 "${row.ReturnID}"？退货后将恢复库存。`, '执行确认', { type: 'success' })
  await saleReturnApi.execute(row.ReturnID)
  ElMessage.success('退货执行成功，已更新库存')
  loadData()
}

const handleRollback = async (row) => {
  await ElMessageBox.confirm(`确定回退退货 "${row.ReturnID}"？回退将扣减库存。`, '回退确认', { type: 'warning' })
  await saleReturnApi.rollback(row.ReturnID)
  ElMessage.success('回退成功')
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该退货单？', '删除确认', { type: 'warning' })
  await saleReturnApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

const drawerOpen = async (id) => {
  const res = await saleReturnApi.get(id)
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
