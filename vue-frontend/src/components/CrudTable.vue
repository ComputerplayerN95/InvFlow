<template>
  <div class="crud-table-wrapper">
    <!-- 工具栏插槽：搜索、按钮等 -->
    <div v-if="$slots.toolbar" class="table-toolbar">
      <slot name="toolbar" />
    </div>

    <el-table
      :data="data"
      border
      stripe
      highlight-current-row
      v-loading="loading"
      :max-height="maxHeight"
      :default-sort="defaultSort"
      @sort-change="handleSortChange"
      style="width: 100%"
    >
      <!-- 序号列 -->
      <el-table-column v-if="showIndex" type="index" label="#" width="50" align="center" />

      <!-- 动态列 -->
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :sortable="col.sortable"
        :align="col.align || 'left'"
        :formatter="col.formatter"
      >
        <template v-if="col.slot" #default="{ row, $index }">
          <slot :name="col.slot" :row="row" :index="$index">
            {{ row[col.prop] }}
          </slot>
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column
        v-if="$slots.action"
        label="操作"
        :width="actionWidth"
        align="center"
        fixed="right"
      >
        <template #default="{ row, $index }">
          <slot name="action" :row="row" :index="$index" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div v-if="showPagination && total > 0" class="table-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="pageSizes"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 空状态 -->
    <EmptyState v-if="!loading && (!data || data.length === 0)" description="暂无数据" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  showPagination: { type: Boolean, default: true },
  showIndex: { type: Boolean, default: true },
  maxHeight: { type: [Number, String], default: 500 },
  actionWidth: { type: [Number, String], default: 220 },
  defaultSort: { type: Object, default: null },
  pageSizes: { type: Array, default: () => [10, 20, 50, 100] },
})

const emit = defineEmits(['page-change', 'size-change', 'sort-change'])

const currentPage = ref(1)
const pageSize = ref(20)

const handlePageChange = (page) => emit('page-change', page)
const handleSizeChange = (size) => {
  pageSize.value = size
  emit('size-change', size)
}
const handleSortChange = (sort) => emit('sort-change', sort)

// 当 data 变化重置分页
watch(() => props.data, () => {
  currentPage.value = 1
})
</script>

<style scoped>
.crud-table-wrapper { width: 100%; }
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}
.table-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
