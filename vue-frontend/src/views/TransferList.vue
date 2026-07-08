<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">调拨管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openCreate">+ 新增调拨单</el-button>
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
        <template #action="{ row }">
          <el-button v-if="row.Status==='草稿'" size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="success" @click="handleApprove(row)">审核</el-button>
          <el-button v-if="row.Status==='已审核'" size="small" type="warning" @click="handleRollback(row)">审核回退</el-button>
          <el-button v-if="row.Status==='草稿'" size="small" type="danger" @click="handleDelete(row.TransferID)">删除</el-button>
          <el-button size="small" @click="drawerOpen(row.TransferID)">详情</el-button>
        </template>
      </CrudTable>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑调拨单':'新增调拨单'" width="800px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="单号" prop="TransferID">
              <el-input v-model="form.TransferID" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="调出仓库" prop="FromWarehouseID">
              <el-select v-model="form.FromWarehouseID" placeholder="请选择" style="width:100%">
                <el-option v-for="w in warehouses" :key="w.WarehouseID" :label="w.WarehouseName" :value="w.WarehouseID" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="调入仓库" prop="ToWarehouseID">
              <el-select v-model="form.ToWarehouseID" placeholder="请选择" style="width:100%">
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
        <span style="font-size:13px;color:#909399">调拨明细（共 {{ details.length }} 项）</span>
      </el-divider>
      <el-table :data="details" border size="small" max-height="300">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="商品" min-width="200">
          <template #default="{row}">
            <el-select v-model="row.ProductID" filterable placeholder="选择商品" style="width:100%">
              <el-option v-for="p in products" :key="p.ProductID" :label="p.ProductName" :value="p.ProductID" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="调拨数量" width="150">
          <template #default="{row}">
            <el-input-number v-model="row.Quantity" :min="1" :precision="0" size="small" controls-position="right" style="width:120px" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link @click="details.splice($index,1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:10px">
        <el-button size="small" @click="addDetail">+ 添加明细</el-button>
      </div>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="调拨单详情" size="600px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="单号">{{ currentOrder.TransferID }}</el-descriptions-item>
          <el-descriptions-item label="状态"><StatusTag :status="currentOrder.Status" /></el-descriptions-item>
          <el-descriptions-item label="调出">{{ currentOrder.FromWarehouseName }}</el-descriptions-item>
          <el-descriptions-item label="调入">{{ currentOrder.ToWarehouseName }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ currentOrder.OrderDate }}</el-descriptions-item>
          <el-descriptions-item label="制单人">{{ currentOrder.Operator || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin:16px 0 8px">调拨明细</h4>
        <el-table :data="currentOrder.Details || []" border size="small">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="ProductID" label="商品编号" width="120" />
          <el-table-column prop="Quantity" label="数量" width="80" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { transferApi, warehouseApi, productApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import StatusTag from '../components/StatusTag.vue'
import { genOrderId, genDetailId } from '../utils/id-generator.js'

const list = ref([])
const warehouses = ref([])
const products = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ TransferID: '', FromWarehouseID: '', ToWarehouseID: '', Operator: '系统' })
const details = ref([])
const drawerVisible = ref(false)
const currentOrder = ref(null)

const columns = [
  { prop: 'TransferID', label: '单号', width: 150 },
  { prop: 'FromWarehouseName', label: '调出仓库', width: 140 },
  { prop: 'ToWarehouseName', label: '调入仓库', width: 140 },
  { prop: 'Status', label: '状态', width: 100, slot: 'status' },
  { prop: 'OrderDate', label: '日期', width: 160 },
  { prop: 'Operator', label: '制单人', width: 100 },
]

const formRules = {
  TransferID: [{ required: true, message: '请输入单号', trigger: 'blur' }],
  FromWarehouseID: [{ required: true, message: '请选择调出仓库', trigger: 'change' }],
  ToWarehouseID: [{ required: true, message: '请选择调入仓库', trigger: 'change' }],
}

const loadData = async () => {
  loading.value = true
  const res = await transferApi.list()
  list.value = res
  loading.value = false
}

const loadRefs = async () => {
  const [w, p] = await Promise.all([warehouseApi.list(), productApi.list()])
  warehouses.value = Array.isArray(w) ? w : (w.data || [])
  products.value = Array.isArray(p) ? p : (p.data || [])
}

const addDetail = () => {
  details.value.push({ TransferDetailID: '', ProductID: '', Quantity: 1 })
}

const openCreate = async () => {
  isEdit.value = false
  form.value = { TransferID: genOrderId('TO'), FromWarehouseID: '', ToWarehouseID: '', Operator: '系统' }
  details.value = []
  await loadRefs()
  dialogVisible.value = true
}

const openEdit = async (row) => {
  isEdit.value = true
  form.value = {
    TransferID: row.TransferID,
    FromWarehouseID: row.FromWarehouseID,
    ToWarehouseID: row.ToWarehouseID,
    Operator: row.Operator
  }
  await loadRefs()

  const res = await transferApi.get(row.TransferID)
  const order = res
  details.value = (order.Details || []).map(d => ({ ...d }))
  dialogVisible.value = true
}

const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    if (details.value.length === 0) { ElMessage.warning('请添加调拨明细'); return }
    if (form.value.FromWarehouseID === form.value.ToWarehouseID) {
      ElMessage.warning('调入调出仓库不能相同')
      return
    }

    saving.value = true
    try {
      const d = details.value.map((item, idx) => ({
        TransferDetailID: item.TransferDetailID || genDetailId('TD', form.value.TransferID, idx + 1),
        ProductID: item.ProductID,
        Quantity: item.Quantity
      }))

      if (isEdit.value) {
        await transferApi.update(form.value.TransferID, { ...form.value, Details: d })
      } else {
        await transferApi.create({ ...form.value, Details: d })
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

const handleApprove = async (row) => {
  await ElMessageBox.confirm(`确定审核 "${row.TransferID}"（${row.FromWarehouseName} → ${row.ToWarehouseName}）？`, '审核确认', { type: 'success' })
  const res = await transferApi.approve(row.TransferID)
  if (res.success === false) {
    ElMessage.warning(res.message)
  } else {
    ElMessage.success('审核通过，出入库同步完成')
    loadData()
  }
}

const handleRollback = async (row) => {
  await ElMessageBox.confirm(`确定回退 "${row.TransferID}" 的审核？`, '回退确认', { type: 'warning' })
  await transferApi.approveRollback(row.TransferID)
  ElMessage.success('审核回退完成')
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该调拨单？', '删除确认', { type: 'warning' })
  await transferApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

const drawerOpen = async (id) => {
  const res = await transferApi.get(id)
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
