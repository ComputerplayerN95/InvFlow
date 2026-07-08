<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">商品类型管理</span>
          <el-button type="primary" @click="openAdd">+ 新增类型</el-button>
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
          <el-button size="small" type="danger" @click="handleDelete(row.CategoryID)">删除</el-button>
        </template>
      </CrudTable>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑类型':'新增类型'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="类型编号" prop="CategoryID">
          <el-input v-model="form.CategoryID" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="类型名称" prop="CategoryName">
          <el-input v-model="form.CategoryName" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.Description" type="textarea" :rows="3" />
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
import { categoryApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ CategoryID: '', CategoryName: '', Description: '' })
const columns = [
  { prop: 'CategoryID', label: '编号', width: 120 },
  { prop: 'CategoryName', label: '类型名称', minWidth: 200 },
  { prop: 'Description', label: '描述', minWidth: 300 },
]
const formRules = {
  CategoryID: [{ required: true, message: '请输入编号', trigger: 'blur' }],
  CategoryName: [{ required: true, message: '请输入类型名称', trigger: 'blur' }],
}

const loadData = async () => {
  loading.value = true
  const res = await categoryApi.list()
  list.value = Array.isArray(res) ? res : (res.data || [])
  loading.value = false
}
const openAdd = () => { isEdit.value = false; form.value = { CategoryID: '', CategoryName: '', Description: '' }; dialogVisible.value = true }
const openEdit = (row) => { isEdit.value = true; form.value = { CategoryID: row.CategoryID, CategoryName: row.CategoryName, Description: row.Description }; dialogVisible.value = true }
const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) { await categoryApi.update(form.value.CategoryID, { CategoryName: form.value.CategoryName, Description: form.value.Description }) }
      else { await categoryApi.create(form.value) }
      dialogVisible.value = false; ElMessage.success(isEdit.value ? '编辑成功' : '新增成功'); loadData()
    } catch(e) { ElMessage.error('保存失败') }
  })
}
const handleDelete = async (id) => { await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' }); await categoryApi.delete(id); ElMessage.success('删除成功'); loadData() }
onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
