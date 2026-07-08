<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    :destroy-on-close="true"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
      :disabled="loading"
    >
      <slot name="form" :form="formData" />
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <slot name="footer">
          <el-button @click="handleCancel" :disabled="loading">取消</el-button>
          <el-button type="primary" @click="handleConfirm" :loading="loading">确定</el-button>
        </slot>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '600px' },
  formData: { type: Object, default: () => ({}) },
  rules: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])
const formRef = ref(null)

const handleConfirm = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    emit('confirm')
  } catch {
    // 校验不通过
  }
}

const handleCancel = () => {
  emit('cancel')
  emit('update:visible', false)
}

const handleClose = () => {
  emit('update:visible', false)
}
</script>

<style scoped>
.dialog-footer { display: flex; justify-content: flex-end; gap: 10px; }
</style>
