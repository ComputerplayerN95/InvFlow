<template>
  <div class="page-container">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 出入库月度明细账 -->
      <el-tab-pane label="月度明细账" name="monthlyDetail">
        <el-card>
          <div style="display:flex;gap:10px;margin-bottom:16px;align-items:center;flex-wrap:wrap">
            <span>选择月份：</span>
            <el-date-picker v-model="detailMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width:160px" />
            <el-select v-model="detailProduct" placeholder="选择商品(可选)" clearable style="width:200px" filterable>
              <el-option v-for="p in products" :key="p.ProductID" :label="`${p.ProductID} - ${p.ProductName}`" :value="p.ProductID" />
            </el-select>
            <el-button type="primary" @click="loadMonthlyDetail">查询</el-button>
          </div>

          <template v-if="detailData">
            <h4 style="margin:16px 0 8px">上月结存</h4>
            <CrudTable :data="detailData.begin_stock || []" :columns="beginStockColumns" :show-pagination="false" :show-index="false" action-width="0" size="small">
              <template #beginAmount="{ row }">{{ row.last_month_end_amount?.toFixed(2) }}</template>
            </CrudTable>

            <h4 style="margin:16px 0 8px">本月入库明细</h4>
            <CrudTable :data="detailData.in_details || []" :columns="inDetailColumns" :show-pagination="false" :show-index="false" action-width="0" size="small">
              <template #inAmount="{ row }">{{ row.in_amount?.toFixed(2) }}</template>
            </CrudTable>

            <h4 style="margin:16px 0 8px">本月出库明细</h4>
            <CrudTable :data="detailData.out_details || []" :columns="outDetailColumns" :show-pagination="false" :show-index="false" action-width="0" size="small">
              <template #outAmount="{ row }">{{ row.out_amount?.toFixed(2) }}</template>
            </CrudTable>

            <h4 style="margin:16px 0 8px">本月结存</h4>
            <CrudTable :data="detailData.end_stock || []" :columns="endStockColumns" :show-pagination="false" :show-index="false" action-width="0" size="small">
              <template #endAmount="{ row }">{{ row.month_end_amount?.toFixed(2) }}</template>
            </CrudTable>
          </template>
        </el-card>
      </el-tab-pane>

      <!-- 销售毛利统计 -->
      <el-tab-pane label="销售毛利统计" name="salesProfit">
        <el-card>
          <div style="display:flex;gap:10px;margin-bottom:16px;align-items:center">
            <span>选择月份：</span>
            <el-date-picker v-model="profitMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width:160px" />
            <el-button type="primary" @click="loadSalesProfit">查询</el-button>
            <el-button @click="exportSalesProfitCSV" :disabled="profitData.length === 0">导出CSV</el-button>
          </div>

          <CrudTable :data="profitData" :columns="profitColumns" :show-pagination="false" :show-index="true" action-width="0">
            <template #saleAmount="{ row }">{{ row.total_sale_amount?.toFixed(2) }}</template>
            <template #avgCost="{ row }">{{ row.avg_cost_price?.toFixed(2) }}</template>
            <template #totalCost="{ row }">{{ row.total_cost_amount?.toFixed(2) }}</template>
            <template #grossProfit="{ row }">
              <span :style="{color: row.gross_profit >= 0 ? '#67C23A' : '#F56C6C'}">{{ row.gross_profit?.toFixed(2) }}</span>
            </template>
          </CrudTable>
        </el-card>
      </el-tab-pane>

      <!-- FIFO 销售毛利统计 -->
      <el-tab-pane label="FIFO销售毛利" name="fifoSalesProfit">
        <el-card>
          <div style="display:flex;gap:10px;margin-bottom:16px;align-items:center">
            <span>选择月份：</span>
            <el-date-picker v-model="fifoProfitMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width:160px" />
            <el-button type="primary" @click="loadFifoSalesProfit">查询</el-button>
            <el-button @click="exportFifoSalesProfitCSV" :disabled="fifoProfitData.length === 0">导出CSV</el-button>
          </div>

          <el-alert title="FIFO 先进先出法计算销售毛利，与均价法对比可分析成本差异" type="info" show-icon :closable="false" style="margin-bottom:12px" />

          <CrudTable :data="fifoProfitData" :columns="fifoProfitColumns" :show-pagination="false" :show-index="true" action-width="0">
            <template #saleAmount="{ row }">{{ row.total_sale_amount?.toFixed(2) }}</template>
            <template #fifoCost="{ row }">{{ (row.total_fifo_cost_amount || 0).toFixed(2) }}</template>
            <template #avgCost="{ row }">{{ (row.avg_price_total_cost || 0).toFixed(2) }}</template>
            <template #fifoProfit="{ row }">
              <span :style="{color: (row.fifo_gross_profit || 0) >= 0 ? '#67C23A' : '#F56C6C'}">{{ (row.fifo_gross_profit || 0).toFixed(2) }}</span>
            </template>
            <template #profitDiff="{ row }">
              <span :style="{color: '#909399'}">{{ ((row.total_fifo_cost_amount || 0) - (row.avg_price_total_cost || 0)).toFixed(2) }}</span>
            </template>
          </CrudTable>
        </el-card>
      </el-tab-pane>

      <!-- FIFO 均价成本对比 -->
      <el-tab-pane label="FIFO成本对比" name="fifoCostComparison">
        <el-card>
          <div style="display:flex;gap:10px;margin-bottom:16px;align-items:center">
            <span>选择月份：</span>
            <el-date-picker v-model="fifoCostMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" style="width:160px" />
            <el-button type="primary" @click="loadFifoCostComparison">查询</el-button>
            <el-button @click="exportFifoCostCSV" :disabled="fifoCostData.length === 0">导出CSV</el-button>
          </div>

          <el-alert title="对比同一月份 FIFO 与均价法的销售成本差异，反映不同计价方式对利润的影响" type="info" show-icon :closable="false" style="margin-bottom:12px" />

          <CrudTable :data="fifoCostData" :columns="fifoCostColumns" :show-pagination="false" :show-index="true" action-width="0">
            <template #saleQty="{ row }">{{ row.total_sale_qty || '-' }}</template>
            <template #fifoCost="{ row }">{{ (row.fifo_total_cost || 0).toFixed(2) }}</template>
            <template #avgCost="{ row }">{{ (row.avg_price_total_cost || 0).toFixed(2) }}</template>
            <template #costDiff="{ row }">
              <span :style="{color: (row.cost_diff || 0) >= 0 ? '#E6A23C' : '#67C23A'}">{{ (row.cost_diff || 0).toFixed(2) }}</span>
            </template>
          </CrudTable>
        </el-card>
      </el-tab-pane>

      <!-- 采购/销售综合查询 -->
      <el-tab-pane label="综合查询" name="query">
        <el-card>
          <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
            <el-select v-model="queryType" style="width:120px">
              <el-option label="采购查询" value="purchase" />
              <el-option label="销售查询" value="sale" />
            </el-select>
            <el-date-picker v-model="queryParams.start_date" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width:150px" />
            <el-date-picker v-model="queryParams.end_date" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width:150px" />

            <el-select v-model="queryParams.supplier_id" v-if="queryType==='purchase'" placeholder="选择供应商" clearable filterable style="width:180px">
              <el-option v-for="s in suppliers" :key="s.SupplierID" :label="`${s.SupplierID} - ${s.SupplierName}`" :value="s.SupplierID" />
            </el-select>
            <el-select v-model="queryParams.customer_id" v-if="queryType==='sale'" placeholder="选择客户" clearable filterable style="width:180px">
              <el-option v-for="c in customers" :key="c.CustomerID" :label="`${c.CustomerID} - ${c.CustomerName}`" :value="c.CustomerID" />
            </el-select>

            <el-select v-model="queryParams.category_id" placeholder="选择类别" clearable filterable style="width:180px">
              <el-option v-for="c in categories" :key="c.CategoryID" :label="`${c.CategoryID} - ${c.CategoryName}`" :value="c.CategoryID" />
            </el-select>
            <el-select v-model="queryParams.product_id" placeholder="选择商品" clearable filterable style="width:200px">
              <el-option v-for="p in products" :key="p.ProductID" :label="`${p.ProductID} - ${p.ProductName}`" :value="p.ProductID" />
            </el-select>

            <el-button type="primary" @click="loadQuery">查询</el-button>
            <el-button @click="exportQueryCSV" :disabled="queryData.length === 0">导出CSV</el-button>
          </div>

          <CrudTable :data="queryData" :columns="queryColumns" :loading="queryLoading" :show-pagination="false" :show-index="true" action-width="0" max-height="450">
            <template #docId="{ row }">{{ row.PurchaseID || row.SaleID }}</template>
            <template #party="{ row }">{{ row.SupplierName || row.CustomerName }}</template>
            <template #unitPrice="{ row }">{{ row.UnitPrice?.toFixed(2) }}</template>
            <template #amount="{ row }">{{ row.Amount?.toFixed(2) }}</template>
            <template #status="{ row }">
              <StatusTag :status="row.Status" />
            </template>
          </CrudTable>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { reportApi, supplierApi, customerApi, categoryApi, productApi } from '../api'
import { ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import StatusTag from '../components/StatusTag.vue'

const activeTab = ref('monthlyDetail')

// 下拉选择数据
const suppliers = ref([])
const customers = ref([])
const categories = ref([])
const products = ref([])

// ---- 月度明细账 ----
const detailMonth = ref('')
const detailProduct = ref('')
const detailData = ref(null)

const beginStockColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名', minWidth: 120 },
  { prop: 'CategoryName', label: '类型', width: 100 },
  { prop: 'Spec', label: '规格', width: 100 },
  { prop: 'last_month_end_qty', label: '上月结存数量', width: 120 },
  { label: '上月结存金额', width: 120, slot: 'beginAmount' },
]

const inDetailColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名', minWidth: 120 },
  { prop: 'PurchaseID', label: '采购单号', width: 140 },
  { prop: 'SupplierName', label: '供应商', minWidth: 120 },
  { prop: 'in_qty', label: '入库数量', width: 100 },
  { prop: 'in_price', label: '单价', width: 80 },
  { label: '金额', width: 100, slot: 'inAmount' },
  { prop: 'operate_date', label: '入库时间', width: 160 },
]

const outDetailColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名', minWidth: 120 },
  { prop: 'SaleID', label: '销售单号', width: 140 },
  { prop: 'CustomerName', label: '客户', minWidth: 120 },
  { prop: 'out_qty', label: '出库数量', width: 100 },
  { label: '金额', width: 100, slot: 'outAmount' },
  { prop: 'operate_date', label: '出库时间', width: 160 },
]

const endStockColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名', minWidth: 120 },
  { prop: 'month_end_qty', label: '期末数量', width: 120 },
  { label: '期末金额', width: 120, slot: 'endAmount' },
]

const loadMonthlyDetail = async () => {
  if (!detailMonth.value) { ElMessage.warning('请选择月份'); return }
  const params = { year_month: detailMonth.value }
  if (detailProduct.value) params.product_id = detailProduct.value
  const r = await reportApi.monthlyDetail(params)
  detailData.value = r.data || r
}

// ---- 销售毛利统计 ----
const profitMonth = ref('')
const profitData = ref([])

const profitColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 140 },
  { prop: 'CategoryName', label: '类型', width: 100 },
  { prop: 'total_sale_qty', label: '销量', width: 80 },
  { label: '销售收入(元)', width: 130, slot: 'saleAmount' },
  { label: '成本均价(元)', width: 120, slot: 'avgCost' },
  { label: '成本总额(元)', width: 130, slot: 'totalCost' },
  { label: '毛利(元)', width: 120, slot: 'grossProfit' },
  { prop: 'profit_rate', label: '毛利率(%)', width: 100 },
]

const loadSalesProfit = async () => {
  if (!profitMonth.value) { ElMessage.warning('请选择月份'); return }
  const r = await reportApi.salesProfit({ year_month: profitMonth.value })
  profitData.value = (r.report || r.data?.report || [])
}

function exportSalesProfitCSV() {
  const headers = ['商品编号', '商品名称', '类型', '销量', '销售收入(元)', '成本均价(元)', '成本总额(元)', '毛利(元)', '毛利率(%)']
  const rows = profitData.value.map(row => [
    row.ProductID, row.ProductName, row.CategoryName, row.total_sale_qty,
    row.total_sale_amount?.toFixed(2), row.avg_cost_price?.toFixed(2),
    row.total_cost_amount?.toFixed(2), row.gross_profit?.toFixed(2), row.profit_rate,
  ])
  downloadCSV(headers, rows, `销售毛利统计_${profitMonth.value || 'all'}.csv`)
}

// ---- 综合查询 ----
const queryLoading = ref(false)
const queryType = ref('purchase')
const queryData = ref([])

const queryColumns = [
  { label: '单据编号', width: 140, slot: 'docId' },
  { label: '关联方', width: 140, slot: 'party' },
  { prop: 'WarehouseName', label: '仓库', width: 110 },
  { prop: 'ProductName', label: '商品', minWidth: 140 },
  { prop: 'CategoryName', label: '类型', width: 100 },
  { prop: 'Quantity', label: '数量', width: 80 },
  { label: '单价', width: 80, slot: 'unitPrice' },
  { label: '金额', width: 100, slot: 'amount' },
  { prop: 'OrderDate', label: '日期', width: 160 },
  { label: '状态', width: 80, slot: 'status' },
]

const queryParams = ref({ start_date: '', end_date: '', supplier_id: '', customer_id: '', category_id: '', product_id: '' })

const loadQuery = async () => {
  queryLoading.value = true
  const p = {}
  Object.entries(queryParams.value).forEach(([k, v]) => { if (v) p[k] = v })
  try {
    if (queryType.value === 'purchase') {
      const r = await reportApi.purchaseQuery(p)
      queryData.value = Array.isArray(r) ? r : (r.data || [])
    } else {
      const r = await reportApi.saleQuery(p)
      queryData.value = Array.isArray(r) ? r : (r.data || [])
    }
  } catch(e) {
    queryData.value = []
  }
  queryLoading.value = false
}

function exportQueryCSV() {
  const headers = ['单据编号', '关联方', '仓库', '商品', '类型', '数量', '单价', '金额', '日期', '状态']
  const rows = queryData.value.map(row => [
    row.PurchaseID || row.SaleID,
    row.SupplierName || row.CustomerName,
    row.WarehouseName, row.ProductName, row.CategoryName,
    row.Quantity, row.UnitPrice?.toFixed(2), row.Amount?.toFixed(2),
    row.OrderDate, row.Status,
  ])
  downloadCSV(headers, rows, `综合查询_${queryType.value}_${new Date().toISOString().slice(0,10)}.csv`)
}

function downloadCSV(headers, rows, filename) {
  const csvContent = [
    headers.join(','),
    ...rows.map(r => r.map(v => `"${v ?? ''}"`).join(',')),
  ].join('\n')
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

// ---- FIFO 销售毛利统计 ----
const fifoProfitMonth = ref('')
const fifoProfitData = ref([])

const fifoProfitColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 140 },
  { prop: 'total_sale_qty', label: '销量', width: 80 },
  { label: '销售收入(元)', width: 130, slot: 'saleAmount' },
  { label: 'FIFO总成本(元)', width: 130, slot: 'fifoCost' },
  { label: '均价总成本(元)', width: 130, slot: 'avgCost' },
  { label: 'FIFO毛利(元)', width: 130, slot: 'fifoProfit' },
  { label: '利润差异(元)', width: 120, slot: 'profitDiff' },
]

const loadFifoSalesProfit = async () => {
  if (!fifoProfitMonth.value) { ElMessage.warning('请选择月份'); return }
  const r = await reportApi.fifoSalesProfit({ year_month: fifoProfitMonth.value })
  fifoProfitData.value = Array.isArray(r) ? r : (r.data?.report || r.report || [])
}

function exportFifoSalesProfitCSV() {
  const headers = ['商品编号','商品名称','销量','销售收入','FIFO总成本','均价总成本','FIFO毛利','利润差异']
  const rows = fifoProfitData.value.map(row => [
    row.ProductID, row.ProductName, row.total_sale_qty,
    (row.total_sale_amount || 0).toFixed(2), (row.total_fifo_cost_amount || 0).toFixed(2),
    (row.avg_price_total_cost || 0).toFixed(2), (row.fifo_gross_profit || 0).toFixed(2),
    ((row.total_fifo_cost_amount || 0) - (row.avg_price_total_cost || 0)).toFixed(2),
  ])
  downloadCSV(headers, rows, `FIFO销售毛利_${fifoProfitMonth.value || 'all'}.csv`)
}

// ---- FIFO 成本对比 ----
const fifoCostMonth = ref('')
const fifoCostData = ref([])

const fifoCostColumns = [
  { prop: 'ProductID', label: '商品编号', width: 120 },
  { prop: 'ProductName', label: '商品名称', minWidth: 140 },
  { label: '销量', width: 80, slot: 'saleQty' },
  { prop: 'fifo_method_cost', label: 'FIFO单价', width: 110 },
  { prop: 'avg_price_method_cost', label: '均价单价', width: 110 },
  { label: 'FIFO总成本(元)', width: 130, slot: 'fifoCost' },
  { label: '均价总成本(元)', width: 130, slot: 'avgCost' },
  { label: '成本差异(元)', width: 120, slot: 'costDiff' },
]

const loadFifoCostComparison = async () => {
  if (!fifoCostMonth.value) { ElMessage.warning('请选择月份'); return }
  const r = await reportApi.fifoCostComparison({ year_month: fifoCostMonth.value })
  fifoCostData.value = Array.isArray(r) ? r : (r.data?.report || r.report || [])
}

function exportFifoCostCSV() {
  const headers = ['商品编号','商品名称','销量','FIFO单价','均价单价','FIFO总成本','均价总成本','成本差异']
  const rows = fifoCostData.value.map(row => [
    row.ProductID, row.ProductName, row.total_sale_qty || '',
    (row.fifo_method_cost || 0).toFixed(2), (row.avg_price_method_cost || 0).toFixed(2),
    (row.fifo_total_cost || 0).toFixed(2), (row.avg_price_total_cost || 0).toFixed(2),
    (row.cost_diff || 0).toFixed(2),
  ])
  downloadCSV(headers, rows, `FIFO成本对比_${fifoCostMonth.value || 'all'}.csv`)
}

// ---- 初始化下拉选项 ----
onMounted(async () => {
  try {
    const [s, cus, cat, p] = await Promise.all([
      supplierApi.list(), customerApi.list(), categoryApi.list(), productApi.list()
    ])
    suppliers.value = Array.isArray(s) ? s : (s.data || [])
    customers.value = Array.isArray(cus) ? cus : (cus.data || [])
    categories.value = Array.isArray(cat) ? cat : (cat.data || [])
    products.value = Array.isArray(p) ? p : (p.data || [])
  } catch(e) { /* handled */ }
})
</script>

<style scoped>
.page-container { padding: var(--page-padding, 20px); }
.page-container :deep(.el-card__body) { padding: 16px; }
</style>
