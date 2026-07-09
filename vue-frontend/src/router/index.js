import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../views/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页' } },
      { path: '/categories', name: 'CategoryList', component: () => import('../views/CategoryList.vue'), meta: { title: '商品类型' } },
      { path: '/warehouses', name: 'WarehouseList', component: () => import('../views/WarehouseList.vue'), meta: { title: '仓库管理' } },
      { path: '/suppliers', name: 'SupplierList', component: () => import('../views/SupplierList.vue'), meta: { title: '供应商管理' } },
      { path: '/customers', name: 'CustomerList', component: () => import('../views/CustomerList.vue'), meta: { title: '客户管理' } },
      { path: '/products', name: 'ProductList', component: () => import('../views/ProductList.vue'), meta: { title: '商品管理' } },
      { path: '/purchases', name: 'PurchaseList', component: () => import('../views/PurchaseList.vue'), meta: { title: '采购管理' } },
      { path: '/sales', name: 'SaleList', component: () => import('../views/SaleList.vue'), meta: { title: '销售管理' } },
      { path: '/transfers', name: 'TransferList', component: () => import('../views/TransferList.vue'), meta: { title: '调拨管理' } },
      { path: '/stock-total', name: 'StockTotal', component: () => import('../views/StockTotal.vue'), meta: { title: '库存总表' } },
      { path: '/stock-warehouse', name: 'StockWarehouse', component: () => import('../views/StockWarehouse.vue'), meta: { title: '仓库库存' } },
      { path: '/stock-monthly', name: 'MonthlySettlement', component: () => import('../views/MonthlySettlement.vue'), meta: { title: '月度结存' } },
      { path: '/stock-checks', name: 'StockCheckList', component: () => import('../views/StockCheckList.vue'), meta: { title: '盘点管理' } },
      { path: '/purchase-returns', name: 'PurchaseReturnList', component: () => import('../views/PurchaseReturnList.vue'), meta: { title: '采购退货' } },
      { path: '/sale-returns', name: 'SaleReturnList', component: () => import('../views/SaleReturnList.vue'), meta: { title: '销售退货' } },
      { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '综合报表' } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
