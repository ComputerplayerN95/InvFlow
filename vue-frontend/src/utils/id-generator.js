/**
 * ID生成工具
 */

/**
 * 生成单据编号
 * @param {string} prefix 前缀，如 'PO', 'SO', 'TO'
 * @returns {string} 格式如 PO20250707001
 */
export function genOrderId(prefix) {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const seq = String(Math.floor(Math.random() * 999) + 1).padStart(3, '0')
  return `${prefix}${y}${m}${d}${seq}`
}

/**
 * 生成明细编号
 * @param {string} orderId 主单编号
 * @param {number} index 序号，从1开始
 * @param {string} prefix 明细前缀，如 'PD', 'SD'
 * @returns {string}
 */
export function genDetailId(prefix, orderId, index) {
  return `${prefix}${orderId}${String(index).padStart(2, '0')}`
}
