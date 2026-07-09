<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">盘点管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openCreate">+ 新增盘点单</el-button>
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
          <el-button v-if="row.Status==='草稿'" size="small" type="success" @click="handleAudit(row)">审核</el-button>
          <el-button v-if="row.Status==='盘点完成'" size="small" type="warning" @click="handleRollback(row)">回退</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="danger" @click="handleDelete(row.CheckID)">删除</el-button>
          <el-button size="small" @click="drawerOpen(row.CheckID)">详情</el-button>
        </template>
      </CrudTable>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑盘点单':'新增盘点单'" width="900px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="盘点单号" prop="CheckID">
              <el-input v-model="form.CheckID" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="仓库" prop="WarehouseID">
              <el-select v-model="form.WarehouseID" placeholder="请选择" style="width:100%" @change="onWarehouseChange">
                <el-option v-for="w in warehouses" :key="w.WarehouseID" :label="w.WarehouseName" :value="w.WarehouseID" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="盘点日期">
              <el-date-picker v-model="form.CheckDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="操作人">
          <el-input v-model="form.Operator" style="width:200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.Remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <el-divider>
        <span style="font-size:13px;color:#909399">盘点明细（共 {{ details.length }} 项）</span>
      </el-divider>
      <el-table :data="details" border size="small" max-height="350">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="商品" min-width="180">
          <template #default="{row}">
            <el-select v-model="row.ProductID" filterable placeholder="选择商品" style="width:100%" @change="onProductChange(row)">
              <el-option v-for="p in products" :key="p.ProductID" :label="`${p.ProductID} - ${p.ProductName}`" :value="p.ProductID" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="账面数量" width="110">
          <template #default="{row}">
            <el-input-number v-model="row.BookQuantity" :min="0" :precision="0" size="small" controls-position="right" disabled style="width:100px" />
          </template>
        </el-table-column>
        <el-table-column label="实盘数量" width="110">
          <template #default="{row}">
            <el-input-number v-model="row.ActualQuantity" :min="0" :precision="0" size="small" controls-position="right" style="width:100px" @change="() => calcDiff(row)" />
          </template>
        </el-table-column>
        <el-table-column label="差异" width="80">
          <template #default="{row}">
            <span :style="{color: row.DiffQuantity === 0 ? '#909399' : row.DiffQuantity > 0 ? '#67C23A' : '#F56C6C', fontWeight:600}">
              {{ row.DiffQuantity >= 0 ? '+' : '' }}{{ row.DiffQuantity }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="110">
          <template #default="{row}">
            <el-input-number v-model="row.UnitPrice" :min="0" :precision="2" size="small" controls-position="right" style="width:100px" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="120">
          <template #default="{row}">
            <el-input v-model="row.Remark" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link @click="details.splice($index,1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:10px">
        <el-button size="small" @click="addDetail">+ 添加盘点商品</el-button>
        <el-button size="small" @click="loadAllProducts">+ 加载全部商品</el-button>
      </div>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="盘点单详情" size="600px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="单号">{{ currentOrder.CheckID }}</el-descriptions-item>
          <el-descriptions-item label="状态"><StatusTag :status="currentOrder.Status" /></el-descriptions-item>
          <el-descriptions-item label="仓库">{{ currentOrder.WarehouseName }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ currentOrder.CheckDate }}</el-descriptions-item>
          <el-descriptions-item label="操作人">{{ currentOrder.Operator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="审核人">{{ currentOrder.AuditOperator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ currentOrder.Remark || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin:16px 0 8px">盘点明细</h4>
        <el-table :data="currentOrder.Details || []" border size="small">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="ProductID" label="商品" width="120" />
          <el-table-column prop="BookQuantity" label="账面" width="80" />
          <el-table-column prop="ActualQuantity" label="实盘" width="80" />
          <el-table-column label="差异" width="80">
            <template #default="{row}">
              <span :style="{color: row.DiffQuantity === 0 ? '#909399' : row.DiffQuantity > 0 ? '#67C23A' : '#F56C6C', fontWeight:600}">
                {{ row.DiffQuantity >= 0 ? '+' : '' }}{{ row.DiffQuantity }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="UnitPrice" label="单价" width="100" />
          <el-table-column prop="Remark" label="备注" min-width="120" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { stockCheckApi, warehouseApi, productApi, stockApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import StatusTag from '../components/StatusTag.vue'
import { genOrderId, genDetailId } from '../utils/id-generator.js'

const list = ref([])
const warehouses = ref([])
const products = ref([])
const warehouseStock = ref({})
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ CheckID: '', WarehouseID: '', CheckDate: '', Operator: '系统', Remark: '' })
const details = ref([])
const drawerVisible = ref(false)
const currentOrder = ref(null)

const columns = [
  { prop: 'CheckID', label: '盘点单号', width: 150 },
  { prop: 'WarehouseName', label: '仓库', width: 140 },
  { prop: 'Status', label: '状态', width: 100, slot: 'status' },
  { prop: 'CheckDate', label: '盘点日期', width: 160 },
  { prop: 'Operator', label: '操作人', width: 100 },
  { prop: 'AuditOperator', label: '审核人', width: 100 },
]

const formRules = {
  CheckID: [{ required: true, message: '请输入盘点单号', trigger: 'blur' }],
  WarehouseID: [{ required: true, message: '请选择仓库', trigger: 'change' }],
}

const loadData = async () => {
  loading.value = true
  const res = await stockCheckApi.list()
  list.value = res
  loading.value = false
}

const loadRefs = async () => {
  const [w, p] = await Promise.all([warehouseApi.list(), productApi.list()])
  warehouses.value = Array.isArray(w) ? w : (w.data || [])
  products.value = Array.isArray(p) ? p : (p.data || [])
}

const loadStockByWarehouse = async (warehouseId) => {
  if (!warehouseId) return
  try {
    const res = await stockApi.warehouse({ warehouse_id: warehouseId })
    const data = Array.isArray(res) ? res : (res.data || [])
    const map = {}
    data.forEach(item => {
      map[item.ProductID] = { Quantity: item.Quantity, ProductName: item.ProductName }
    })
    warehouseStock.value = map
  } catch(e) {
    warehouseStock.value = {}
  }
}

const onWarehouseChange = async (val) => {
  await loadStockByWarehouse(val)
  details.value.forEach(d => {
    const stock = warehouseStock.value[d.ProductID]
    if (stock) {
      d.BookQuantity = stock.Quantity
    }
  })
}

const onProductChange = (row) => {
  const stock = warehouseStock.value[row.ProductID]
  if (stock) {
    row.BookQuantity = stock.Quantity
  }
  calcDiff(row)
}

const calcDiff = (row) => {
  row.DiffQuantity = (row.ActualQuantity || 0) - (row.BookQuantity || 0)
}

const addDetail = () => {
  details.value.push({
    CheckDetailID: '', ProductID: '', BookQuantity: 0,
    ActualQuantity: 0, DiffQuantity: 0, UnitPrice: 0, Remark: ''
  })
}

const loadAllProducts = async () => {
  if (!form.value.WarehouseID) { ElMessage.warning('请先选择仓库'); return }
  await loadStockByWarehouse(form.value.WarehouseID)
  const existing = new Set(details.value.map(d => d.ProductID))
  products.value.forEach(p => {
    if (!existing.has(p.ProductID)) {
      const stock = warehouseStock.value[p.ProductID]
      details.value.push({
        CheckDetailID: '',
        ProductID: p.ProductID,
        BookQuantity: stock ? stock.Quantity : 0,
        ActualQuantity: stock ? stock.Quantity : 0,
        DiffQuantity: 0,
        UnitPrice: 0,
        Remark: ''
      })
    }
  })
}

const openCreate = async () => {
  isEdit.value = false
  form.value = { CheckID: genOrderId('CK'), WarehouseID: '', CheckDate: new Date().toISOString().slice(0,19), Operator: '系统', Remark: '' }
  details.value = []
  await loadRefs()
  dialogVisible.value = true
}

const openEdit = async (row) => {
  isEdit.value = true
  form.value = {
    CheckID: row.CheckID, WarehouseID: row.WarehouseID,
    CheckDate: row.CheckDate, Operator: row.Operator, Remark: row.Remark
  }
  await loadRefs()
  await loadStockByWarehouse(row.WarehouseID)
  const res = await stockCheckApi.get(row.CheckID)
  const order = res
  details.value = (order.Details || []).map(d => ({ ...d }))
  dialogVisible.value = true
}

const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    if (details.value.length === 0) { ElMessage.warning('请添加盘点商品'); return }
    saving.value = true
    try {
      const d = details.value.map((item, idx) => ({
        CheckDetailID: item.CheckDetailID || genDetailId('CD', form.value.CheckID, idx + 1),
        ProductID: item.ProductID,
        BookQuantity: item.BookQuantity || 0,
        ActualQuantity: item.ActualQuantity || 0,
        DiffQuantity: (item.ActualQuantity || 0) - (item.BookQuantity || 0),
        UnitPrice: item.UnitPrice || 0,
        Remark: item.Remark || ''
      }))
      if (isEdit.value) {
        await stockCheckApi.update(form.value.CheckID, { ...form.value, Details: d })
      } else {
        await stockCheckApi.create({ ...form.value, Details: d })
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

const handleAudit = async (row) => {
  await ElMessageBox.confirm(`确定审核盘点单 "${row.CheckID}"（${row.WarehouseName}）？审核后将自动生成损益单。`, '审核确认', { type: 'success' })
  await stockCheckApi.audit(row.CheckID)
  ElMessage.success('审核完成，已自动处理库存差异')
  loadData()
}

const handleRollback = async (row) => {
  await ElMessageBox.confirm(`确定回退盘点单 "${row.CheckID}"？回退将撤销库存调整。`, '回退确认', { type: 'warning' })
  await stockCheckApi.rollback(row.CheckID)
  ElMessage.success('回退成功')
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该盘点单？', '删除确认', { type: 'warning' })
  await stockCheckApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

const drawerOpen = async (id) => {
  const res = await stockCheckApi.get(id)
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
