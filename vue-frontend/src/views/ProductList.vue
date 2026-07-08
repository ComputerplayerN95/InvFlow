<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span style="font-size:16px;font-weight:600">商品管理</span>
          <div>
            <el-input v-model="searchQuery" placeholder="搜索商品名称..." prefix-icon="Search" style="width:200px;margin-right:10px" clearable @clear="loadData" @keyup.enter="loadData" />
            <el-button type="primary" @click="openAdd">+ 新增商品</el-button>
          </div>
        </div>
      </template>

      <CrudTable
        :data="filteredList"
        :columns="columns"
        :loading="loading"
        :show-pagination="false"
        :show-index="true"
        action-width="200"
      >
        <template #action="{ row }">
          <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.ProductID)">删除</el-button>
        </template>
      </CrudTable>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit?'编辑商品':'新增商品'" width="550px" destroy-on-close>
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="商品编号" prop="ProductID">
          <el-input v-model="form.ProductID" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="商品名称" prop="ProductName">
          <el-input v-model="form.ProductName" />
        </el-form-item>
        <el-form-item label="商品类型" prop="CategoryID">
          <el-select v-model="form.CategoryID" placeholder="请选择" style="width:100%">
            <el-option v-for="c in categories" :key="c.CategoryID" :label="c.CategoryName" :value="c.CategoryID" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格"><el-input v-model="form.Spec" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="form.Unit" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.Remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { productApi, categoryApi } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'

const list = ref([])
const categories = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const searchQuery = ref('')

const form = ref({ ProductID: '', ProductName: '', CategoryID: '', Spec: '', Unit: '', Remark: '' })

const columns = [
  { prop: 'ProductID', label: '编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 150 },
  { prop: 'CategoryName', label: '类型', width: 120 },
  { prop: 'Spec', label: '规格', width: 150 },
  { prop: 'Unit', label: '单位', width: 80 },
]

const formRules = {
  ProductID: [{ required: true, message: '请输入商品编号', trigger: 'blur' }],
  ProductName: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  CategoryID: [{ required: true, message: '请选择商品类型', trigger: 'change' }],
}

const filteredList = computed(() => {
  if (!searchQuery.value) return list.value
  return list.value.filter(item =>
    item.ProductName?.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const loadData = async () => {
  loading.value = true
  const res = await productApi.list()
  list.value = Array.isArray(res) ? res : (res.data || [])
  const cRes = await categoryApi.list()
  categories.value = Array.isArray(cRes) ? cRes : (cRes.data || [])
  loading.value = false
}

const openAdd = () => {
  isEdit.value = false
  form.value = { ProductID: '', ProductName: '', CategoryID: '', Spec: '', Unit: '', Remark: '' }
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = { ProductID: row.ProductID, ProductName: row.ProductName, CategoryID: row.CategoryID, Spec: row.Spec, Unit: row.Unit, Remark: row.Remark }
  dialogVisible.value = true
}

const handleSave = async () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return
    try {
      if (isEdit.value) {
        await productApi.update(form.value.ProductID, {
          ProductName: form.value.ProductName,
          CategoryID: form.value.CategoryID,
          Spec: form.value.Spec,
          Unit: form.value.Unit,
          Remark: form.value.Remark
        })
      } else {
        await productApi.create(form.value)
      }
      dialogVisible.value = false
      ElMessage.success(isEdit.value ? '编辑成功' : '新增成功')
      loadData()
    } catch (e) {
      ElMessage.error('保存失败')
    }
  })
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该商品？', '删除确认', { type: 'warning' })
  await productApi.delete(id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
