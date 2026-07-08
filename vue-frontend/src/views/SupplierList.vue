<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">供应商管理</span>
          <el-button type="primary" @click="openAdd">+ 新增供应商</el-button>
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
          <el-button size="small" type="danger" @click="handleDelete(row.SupplierID)">删除</el-button>
        </template>
      </CrudTable>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑供应商':'新增供应商'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="供应商编号" prop="SupplierID">
          <el-input v-model="form.SupplierID" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="供应商名称" prop="SupplierName">
          <el-input v-model="form.SupplierName" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.Contact" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.Phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.Address" />
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
import { supplierApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ SupplierID: '', SupplierName: '', Contact: '', Phone: '', Address: '' })
const columns = [
  { prop: 'SupplierID', label: '编号', width: 120 },
  { prop: 'SupplierName', label: '供应商名称', minWidth: 200 },
  { prop: 'Contact', label: '联系人', width: 100 },
  { prop: 'Phone', label: '电话', width: 140 },
  { prop: 'Address', label: '地址', minWidth: 250 },
]
const formRules = {
  SupplierID: [{ required: true, message: '请输入编号', trigger: 'blur' }],
  SupplierName: [{ required: true, message: '请输入供应商名称', trigger: 'blur' }],
}

const loadData = async () => {
  loading.value = true
  const res = await supplierApi.list()
  list.value = Array.isArray(res) ? res : (res.data || [])
  loading.value = false
}
const openAdd = () => { isEdit.value = false; form.value = { SupplierID: '', SupplierName: '', Contact: '', Phone: '', Address: '' }; dialogVisible.value = true }
const openEdit = (row) => { isEdit.value = true; form.value = { SupplierID: row.SupplierID, SupplierName: row.SupplierName, Contact: row.Contact, Phone: row.Phone, Address: row.Address }; dialogVisible.value = true }
const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) { await supplierApi.update(form.value.SupplierID, { SupplierName: form.value.SupplierName, Contact: form.value.Contact, Phone: form.value.Phone, Address: form.value.Address }) }
      else { await supplierApi.create(form.value) }
      dialogVisible.value = false; ElMessage.success(isEdit.value ? '编辑成功' : '新增成功'); loadData()
    } catch(e) { ElMessage.error('保存失败') }
  })
}
const handleDelete = async (id) => { await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' }); await supplierApi.delete(id); ElMessage.success('删除成功'); loadData() }
onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
