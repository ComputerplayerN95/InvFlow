<template>
  <el-tag :type="tagType" :hit="false" effect="light" size="small">
    {{ status }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: '' }
})

const statusMap = {
  '已入库': 'success',
  '已出库': 'success',
  '已审核': 'success',
  '草稿': 'warning',
  '已回退': 'info',
  '已退货': 'danger',
  '部分退货': 'warning',
  '盘点完成': 'success',
  '待盘点': 'warning',
}

const tagType = computed(() => statusMap[props.status] || 'info')
</script>
