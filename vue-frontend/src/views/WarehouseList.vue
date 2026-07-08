<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">仓库管理</span>
          <el-button type="primary" @click="openAdd">+ 新增仓库</el-button>
        </div>
      </template>

      <CrudTable
        :data="list"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="true"
        action-width="160"
      >
        <template #action="{ row }">
          <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.WarehouseID)">删除</el-button>
        </template>
      </CrudTable>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑仓库':'新增仓库'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="仓库编号" prop="WarehouseID">
          <el-input v-model="form.WarehouseID" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="仓库名称" prop="WarehouseName">
          <el-input v-model="form.WarehouseName" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.Location" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.Phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { warehouseApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ WarehouseID: '', WarehouseName: '', Location: '', Phone: '' })
const columns = [
  { prop: 'WarehouseID', label: '编号', width: 120 },
  { prop: 'WarehouseName', label: '仓库名称', minWidth: 200 },
  { prop: 'Location', label: '地址', minWidth: 250 },
  { prop: 'Phone', label: '电话', width: 150 },
]
const formRules = {
  WarehouseID: [{ required: true, message: '请输入编号', trigger: 'blur' }],
  WarehouseName: [{ required: true, message: '请输入仓库名称', trigger: 'blur' }],
}

const loadData = async () => {
  loading.value = true
  const res = await warehouseApi.list()
  list.value = Array.isArray(res) ? res : (res.data || [])
  loading.value = false
}
const openAdd = () => { isEdit.value = false; form.value = { WarehouseID: '', WarehouseName: '', Location: '', Phone: '' }; dialogVisible.value = true }
const openEdit = (row) => { isEdit.value = true; form.value = { WarehouseID: row.WarehouseID, WarehouseName: row.WarehouseName, Location: row.Location, Phone: row.Phone }; dialogVisible.value = true }
const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) { await warehouseApi.update(form.value.WarehouseID, { WarehouseName: form.value.WarehouseName, Location: form.value.Location, Phone: form.value.Phone }) }
      else { await warehouseApi.create(form.value) }
      dialogVisible.value = false; ElMessage.success(isEdit.value ? '编辑成功' : '新增成功'); loadData()
    } catch(e) { ElMessage.error('保存失败') }
  })
}
const handleDelete = async (id) => { await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' }); await warehouseApi.delete(id); ElMessage.success('删除成功'); loadData() }
onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
