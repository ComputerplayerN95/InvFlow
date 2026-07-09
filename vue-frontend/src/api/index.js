import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求拦截器 - 增加 loading 状态
api.interceptors.request.use(
  config => {
    // 可在此添加 token 等
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  response => response.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

export default api

// ==================== 基础数据 API ====================
export const categoryApi = {
  list: () => api.get('/categories/'),
  get: (id) => api.get(`/categories/${id}`),
  create: (data) => api.post('/categories/', data),
  update: (id, data) => api.put(`/categories/${id}`, data),
  delete: (id) => api.delete(`/categories/${id}`),
}

export const warehouseApi = {
  list: () => api.get('/warehouses/'),
  get: (id) => api.get(`/warehouses/${id}`),
  create: (data) => api.post('/warehouses/', data),
  update: (id, data) => api.put(`/warehouses/${id}`, data),
  delete: (id) => api.delete(`/warehouses/${id}`),
}

export const supplierApi = {
  list: () => api.get('/suppliers/'),
  get: (id) => api.get(`/suppliers/${id}`),
  create: (data) => api.post('/suppliers/', data),
  update: (id, data) => api.put(`/suppliers/${id}`, data),
  delete: (id) => api.delete(`/suppliers/${id}`),
}

export const customerApi = {
  list: () => api.get('/customers/'),
  get: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers/', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  delete: (id) => api.delete(`/customers/${id}`),
}

export const productApi = {
  list: () => api.get('/products/'),
  get: (id) => api.get(`/products/${id}`),
  create: (data) => api.post('/products/', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
  getSuppliers: (id) => api.get(`/products/${id}/suppliers`),
  addSupplier: (data) => api.post('/products/suppliers', data),
  removeSupplier: (id) => api.delete(`/products/suppliers/${id}`),
}

// ==================== 采购单 API ====================
export const purchaseApi = {
  list: (params) => api.get('/purchases/', { params }),
  get: (id) => api.get(`/purchases/${id}`),
  create: (data) => api.post('/purchases/', data),
  update: (id, data) => api.put(`/purchases/${id}`, data),
  delete: (id) => api.delete(`/purchases/${id}`),
  addDetail: (id, data) => api.post(`/purchases/${id}/details`, data),
  removeDetail: (id, did) => api.delete(`/purchases/${id}/details/${did}`),
  inStock: (id, operator) => api.post(`/purchases/${id}/in-stock?operator=${operator}`),
  rollback: (id, operator) => api.post(`/purchases/${id}/in-stock-rollback?operator=${operator}`),
  inStockRollback: (id) => api.post(`/purchases/${id}/in-stock-rollback`),
}

// ==================== 销售单 API ====================
export const saleApi = {
  list: (params) => api.get('/sales/', { params }),
  get: (id) => api.get(`/sales/${id}`),
  create: (data) => api.post('/sales/', data),
  update: (id, data) => api.put(`/sales/${id}`, data),
  delete: (id) => api.delete(`/sales/${id}`),
  addDetail: (id, data) => api.post(`/sales/${id}/details`, data),
  removeDetail: (id, did) => api.delete(`/sales/${id}/details/${did}`),
  outStock: (id, operator) => api.post(`/sales/${id}/out-stock?operator=${operator}`),
  rollback: (id, operator) => api.post(`/sales/${id}/out-stock-rollback?operator=${operator}`),
  outStockRollback: (id) => api.post(`/sales/${id}/out-stock-rollback`),
}

// ==================== 调拨单 API ====================
export const transferApi = {
  list: (params) => api.get('/transfers/', { params }),
  get: (id) => api.get(`/transfers/${id}`),
  create: (data) => api.post('/transfers/', data),
  update: (id, data) => api.put(`/transfers/${id}`, data),
  delete: (id) => api.delete(`/transfers/${id}`),
  approve: (id) => api.post(`/transfers/${id}/approve`),
  approveRollback: (id) => api.post(`/transfers/${id}/approve-rollback`),
}

// ==================== 库存 API ====================
export const stockApi = {
  total: (params) => api.get('/stock/total', { params }),
  warehouse: (params) => api.get('/stock/warehouse', { params }),
  monthlyList: (params) => api.get('/stock/monthly', { params }),
  monthlySettle: (data) => api.post('/stock/monthly/settle', data),
  monthlyAntiSettle: (data) => api.post('/stock/monthly/anti-settle', data),
  summaryByCategory: () => api.get('/stock/summary/by-category'),
}

// ==================== 报表 API ====================
export const reportApi = {
  monthlyDetail: (params) => api.get('/reports/monthly-detail', { params }),
  monthlySalesProfit: (params) => api.get('/reports/monthly-sales-profit', { params }),
  salesProfit: (params) => api.get('/reports/monthly-sales-profit', { params }),
  purchaseQuery: (params) => api.get('/reports/purchase-query', { params }),
  saleQuery: (params) => api.get('/reports/sale-query', { params }),
  // FIFO 报表
  fifoSalesProfit: (params) => api.get('/reports/fifo-sales-profit', { params }),
  fifoCostComparison: (params) => api.get('/reports/fifo-cost-comparison', { params }),
}

// ==================== 采购退货 API ====================
export const purchaseReturnApi = {
  list: (params) => api.get('/purchase-returns/', { params }),
  get: (id) => api.get(`/purchase-returns/${id}`),
  create: (data) => api.post('/purchase-returns/', data),
  update: (id, data) => api.put(`/purchase-returns/${id}`, data),
  delete: (id) => api.delete(`/purchase-returns/${id}`),
  execute: (id) => api.post(`/purchase-returns/${id}/execute`),
  rollback: (id) => api.post(`/purchase-returns/${id}/rollback`),
}

// ==================== 销售退货 API ====================
export const saleReturnApi = {
  list: (params) => api.get('/sale-returns/', { params }),
  get: (id) => api.get(`/sale-returns/${id}`),
  create: (data) => api.post('/sale-returns/', data),
  update: (id, data) => api.put(`/sale-returns/${id}`, data),
  delete: (id) => api.delete(`/sale-returns/${id}`),
  execute: (id) => api.post(`/sale-returns/${id}/execute`),
  rollback: (id) => api.post(`/sale-returns/${id}/rollback`),
}

// ==================== 盘点 API ====================
export const stockCheckApi = {
  list: (params) => api.get('/stock-checks/', { params }),
  get: (id) => api.get(`/stock-checks/${id}`),
  create: (data) => api.post('/stock-checks/', data),
  update: (id, data) => api.put(`/stock-checks/${id}`, data),
  delete: (id) => api.delete(`/stock-checks/${id}`),
  audit: (id) => api.post(`/stock-checks/${id}/audit`),
  rollback: (id) => api.post(`/stock-checks/${id}/rollback`),
}

// ==================== 损益单 API ====================
export const profitLossApi = {
  list: (params) => api.get('/profit-loss/', { params }),
  get: (id) => api.get(`/profit-loss/${id}`),
  create: (data) => api.post('/profit-loss/', data),
  update: (id, data) => api.put(`/profit-loss/${id}`, data),
  delete: (id) => api.delete(`/profit-loss/${id}`),
  audit: (id) => api.post(`/profit-loss/${id}/audit`),
  rollback: (id) => api.post(`/profit-loss/${id}/rollback`),
}
