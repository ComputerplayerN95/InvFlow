<template>
  <el-empty :description="description" :image-size="imageSize">
    <template v-if="$slots.default">
      <slot />
    </template>
  </el-empty>
</template>

<script setup>
defineProps({
  description: { type: String, default: '暂无数据' },
  imageSize: { type: Number, default: 150 }
})
</script>
