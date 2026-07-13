<template>
  <div class="chat-assistant">
    <!-- 浮动按钮（可拖动） -->
    <div class="float-btn" :class="{ active: visible }"
      :style="btnStyle"
      @mousedown.prevent="startBtnDrag">
      <svg v-if="!visible" viewBox="0 0 24 24" width="28" height="28">
        <path d="M5 9a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V9z" fill="#fff"/>
        <line x1="6" y1="11" x2="18" y2="11" stroke="#337ecc" stroke-width="0.8" opacity="0.25"/>
        <circle cx="9.5" cy="14.5" r="1.3" fill="#337ecc"/><circle cx="14.5" cy="14.5" r="1.3" fill="#337ecc"/>
        <path d="M10.5 17a2 2 0 0 0 3 0" fill="none" stroke="#337ecc" stroke-width="1.2" stroke-linecap="round"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </div>

    <!-- 聊天面板（可拖动标题栏） -->
    <transition name="slide">
      <div v-if="visible" class="chat-panel"
        :style="panelStyle">
        <div class="chat-header" @mousedown.prevent="startDrag">
          <div class="header-info">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M5.5 9a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v8.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1V9z" fill="#fff"/>
              <line x1="6.5" y1="11" x2="17.5" y2="11" stroke="#409EFF" stroke-width="0.7" opacity="0.3"/>
              <circle cx="9.5" cy="14" r="1.2" fill="#409EFF"/><circle cx="14.5" cy="14" r="1.2" fill="#409EFF"/>
              <path d="M10.5 16.5a1.5 1.5 0 0 0 3 0" fill="none" stroke="#409EFF" stroke-width="1" stroke-linecap="round"/>
            </svg>
            <span>小库 AI 助手</span>
          </div>
          <div class="header-actions">
            <el-tooltip content="清空对话" placement="bottom">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" class="header-icon" @click.stop="clearChat">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </el-tooltip>
          </div>
        </div>

        <div class="chat-messages" ref="msgContainer">
          <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
            <div class="avatar" :class="msg.role">
              <svg v-if="msg.role==='assistant'" viewBox="0 0 24 24" width="16" height="16">
                <path d="M5.5 8.5a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-9z" fill="#fff"/>
                <line x1="6.5" y1="10.5" x2="17.5" y2="10.5" stroke="#337ecc" stroke-width="0.6" opacity="0.25"/>
                <circle cx="9.5" cy="13.5" r="1.1" fill="#337ecc"/><circle cx="14.5" cy="13.5" r="1.1" fill="#337ecc"/>
                <path d="M10.5 16a1.5 1.5 0 0 0 3 0" fill="none" stroke="#337ecc" stroke-width="0.9" stroke-linecap="round"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="#fff">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="bubble">
              <div class="bubble-text" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>
          <div v-if="loading" class="message assistant">
            <div class="avatar assistant">
              <svg viewBox="0 0 24 24" width="16" height="16">
                <path d="M5.5 8.5a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-9z" fill="#fff"/>
                <line x1="6.5" y1="10.5" x2="17.5" y2="10.5" stroke="#337ecc" stroke-width="0.6" opacity="0.25"/>
                <circle cx="9.5" cy="13.5" r="1.1" fill="#337ecc"/><circle cx="14.5" cy="13.5" r="1.1" fill="#337ecc"/>
                <path d="M10.5 16a1.5 1.5 0 0 0 3 0" fill="none" stroke="#337ecc" stroke-width="0.9" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="bubble thinking">
              <span class="dot-pulse"></span>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="问问小库：帮我查库存、调拨方案、业务流程..."
            resize="none"
            @keydown.enter.prevent="sendMessage"
            :disabled="loading"
          />
          <el-button type="primary" :loading="loading" @click="sendMessage" class="send-btn">
            发送
          </el-button>
        </div>

        <div class="chat-footer">
          <span class="suggestion" @click="quickQuery('帮我查一下所有商品的库存')">查库存</span>
          <span class="suggestion" @click="quickQuery('FIFO先进先出法是什么')">什么是FIFO</span>
          <span class="suggestion" @click="quickQuery('如何做采购退货')">如何退货</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

// Markdown 渲染
marked.setOptions({ breaks: true, gfm: true })
function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

// ========== Session ID（localStorage 持久化） ==========
const SESSION_KEY = 'invflow_chat_session'
function getOrCreateSessionId() {
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}
const sessionId = ref(getOrCreateSessionId())

// ========== 位置状态（localStorage 持久化） ==========
const POS_KEY = 'invflow_chat_pos'
function loadPositions() {
  try {
    const saved = localStorage.getItem(POS_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return null
}
function savePositions() {
  localStorage.setItem(POS_KEY, JSON.stringify({
    btn: btnPos.value, panel: panelPos.value
  }))
}

const defaultPos = loadPositions()
const btnPos = ref(defaultPos?.btn || { x: null, y: null })
const panelPos = ref(defaultPos?.panel || { x: null, y: null })

// 计算样式：x/y 为 null 时不覆盖默认 CSS（right/bottom 定位）
const btnStyle = computed(() => ({
  left: btnPos.value.x != null ? btnPos.value.x + 'px' : undefined,
  top: btnPos.value.y != null ? btnPos.value.y + 'px' : undefined,
}))
const panelStyle = computed(() => ({
  left: panelPos.value.x != null ? panelPos.value.x + 'px' : undefined,
  top: panelPos.value.y != null ? panelPos.value.y + 'px' : undefined,
}))

// ========== 消息 ==========
const visible = ref(false)
const messages = ref([
  { role: 'assistant', content: '你好！我是小库 🤖\n我可以帮你查库存、检查缺货、生成调拨方案、回答业务流程问题。\n有什么需要帮忙的吗？' }
])
const inputText = ref('')
const loading = ref(false)
const msgContainer = ref(null)

function togglePanel() {
  visible.value = !visible.value
}

async function clearChat() {
  messages.value = [{ role: 'assistant', content: '对话已清空，有需要随时找我！' }]
  try {
    const sid = sessionId.value
    localStorage.removeItem(SESSION_KEY)
    sessionId.value = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(SESSION_KEY, sessionId.value)
  } catch {}
}

function scrollToBottom() {
  nextTick(() => {
    const el = msgContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
watch(messages, scrollToBottom, { deep: true })

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  try {
    const history = messages.value.slice(1, -1).map(m => ({
      role: m.role, content: m.content
    }))
    const res = await axios.post('/api/agent/chat', {
      message: text,
      session_id: sessionId.value,
      history: history
    })
    const data = res.data
    messages.value.push({
      role: 'assistant',
      content: data.response || '抱歉，处理出错了。'
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，连接助手服务失败了。请确保后端已启动。'
    })
  } finally {
    loading.value = false
  }
}

function quickQuery(text) {
  inputText.value = text
  sendMessage()
}

// ========== 拖动逻辑（聊天面板标题栏） ==========
let dragging = false
let dragStart = { x: 0, y: 0 }
let dragOrig = { x: 0, y: 0 }

function startDrag(e) {
  dragging = true
  dragStart = { x: e.clientX, y: e.clientY }
  dragOrig = { x: panelPos.value.x || (window.innerWidth - 420), y: panelPos.value.y || 162 }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(e) {
  if (!dragging) return
  panelPos.value = {
    x: dragOrig.x + (e.clientX - dragStart.x),
    y: dragOrig.y + (e.clientY - dragStart.y),
  }
}

function stopDrag() {
  dragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  savePositions()
}

// ========== 拖动逻辑（浮动按钮） ==========
let btnDragging = false
let btnDragStart = { x: 0, y: 0 }
let btnDragOrig = { x: 0, y: 0 }

function startBtnDrag(e) {
  btnDragging = true
  btnDragStart = { x: e.clientX, y: e.clientY }
  btnDragOrig = {
    x: btnPos.value.x || (window.innerWidth - 76),
    y: btnPos.value.y || 100,
  }
  document.addEventListener('mousemove', onBtnDrag)
  document.addEventListener('mouseup', stopBtnDrag)
}

function onBtnDrag(e) {
  if (!btnDragging) return
  btnPos.value = {
    x: btnDragOrig.x + (e.clientX - btnDragStart.x),
    y: btnDragOrig.y + (e.clientY - btnDragStart.y),
  }
}

function stopBtnDrag(e) {
  btnDragging = false
  document.removeEventListener('mousemove', onBtnDrag)
  document.removeEventListener('mouseup', stopBtnDrag)
  // 如果拖动超过 5px 视为拖动，不触发放置 toggle
  const dx = e.clientX - btnDragStart.x
  const dy = e.clientY - btnDragStart.y
  if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
    // 真正拖动时不 toggle
  } else {
    togglePanel()
  }
  savePositions()
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('mousemove', onBtnDrag)
  document.removeEventListener('mouseup', stopBtnDrag)
})
</script>

<style scoped>
.chat-assistant { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

/* 浮动按钮（绝对定位，由 style 控制 left/top，默认右下角） */
.float-btn {
  position: fixed;
  right: 24px;
  bottom: 100px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  box-shadow: 0 4px 16px rgba(64,158,255,0.4);
  z-index: 9999;
  transition: box-shadow 0.3s ease;
}
.float-btn:active { cursor: grabbing; }
.float-btn:hover { box-shadow: 0 6px 20px rgba(64,158,255,0.5); }
.float-btn.active { background: #F56C6C; }

/* 聊天面板（绝对定位，由 style 控制 left/top，默认右下角） */
.chat-panel {
  position: fixed;
  right: 24px;
  bottom: 162px;
  width: 380px;
  height: 520px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  z-index: 9998;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(16px) scale(0.96); }

/* 头部（可拖动） */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: #fff;
  cursor: grab;
  user-select: none;
}
.chat-header:active { cursor: grabbing; }
.header-info { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; }
.header-icon { cursor: pointer; opacity: 0.8; transition: opacity 0.2s; }
.header-icon:hover { opacity: 1; }

/* 消息区 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  background: #f5f7fa;
}
.message {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: flex-start;
}
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.avatar.assistant { background: #409EFF; }
.avatar.user { background: #909399; }
.bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px; line-height: 1.6; color: #303133;
}
.message.assistant .bubble { background: #fff; border: 1px solid #e4e7ed; border-top-left-radius: 2px; }
.message.user .bubble { background: #409EFF; color: #fff; border-top-right-radius: 2px; }
.bubble-text { word-break: break-word; }
.bubble-text :deep(table) { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 12px; }
.bubble-text :deep(th), .bubble-text :deep(td) { border: 1px solid #d0d5dd; padding: 4px 8px; text-align: left; }
.bubble-text :deep(th) { background: #f2f3f5; font-weight: 600; }
.bubble-text :deep(code) { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
.bubble-text :deep(pre) { background: #f5f7fa; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }
.bubble-text :deep(pre code) { background: none; padding: 0; }
.bubble-text :deep(ul), .bubble-text :deep(ol) { padding-left: 20px; margin: 4px 0; }
.bubble-text :deep(li) { margin: 2px 0; }
.bubble-text :deep(h1), .bubble-text :deep(h2), .bubble-text :deep(h3) { font-size: 14px; margin: 8px 0 4px; }
.bubble-text :deep(p) { margin: 4px 0; }
.bubble-text :deep(a) { color: #409EFF; }
.bubble-text :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 8px 0; }

.thinking { padding: 12px 16px; }
.dot-pulse {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #409EFF;
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* 输入区 */
.chat-input {
  padding: 10px 12px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  display: flex; gap: 8px; align-items: flex-start;
}
.chat-input :deep(.el-textarea__inner) { font-size: 13px; border-radius: 8px; }
.send-btn { flex-shrink: 0; margin-top: 0; }

/* 快捷建议 */
.chat-footer {
  padding: 8px 12px 10px;
  border-top: 1px solid #f0f0f0;
  display: flex; gap: 6px; flex-wrap: wrap;
}
.suggestion {
  font-size: 12px; color: #409EFF;
  background: #ecf5ff; padding: 3px 10px; border-radius: 12px;
  cursor: pointer; transition: all 0.2s;
}
.suggestion:hover { background: #409EFF; color: #fff; }
</style>
