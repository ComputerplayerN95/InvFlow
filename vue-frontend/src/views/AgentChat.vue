<template>
  <div class="agent-page">
    <div class="agent-card">
      <!-- 头部 -->
      <div class="agent-header">
        <svg viewBox="0 0 24 24" width="22" height="22">
          <path d="M5 8.5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9z" fill="#409EFF"/>
          <line x1="6" y1="10.5" x2="18" y2="10.5" stroke="#fff" stroke-width="0.7" opacity="0.3"/>
          <circle cx="9.5" cy="13.5" r="1.2" fill="#fff"/><circle cx="14.5" cy="13.5" r="1.2" fill="#fff"/>
          <path d="M10.5 16.5a1.5 1.5 0 0 0 3 0" fill="none" stroke="#fff" stroke-width="1" stroke-linecap="round"/>
        </svg>
        <span class="agent-title">小库 AI 智能助手</span>
        <span class="agent-subtitle">自然语言驱动 · 自动查库存 · 智能调拨 · 流程问答</span>
        <el-button size="small" circle @click="clearChat" class="clear-btn">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </el-button>
      </div>

      <!-- 消息区 -->
      <div class="agent-messages" ref="msgContainer">
        <div class="msg-list">
          <div v-for="(msg, i) in messages" :key="i" :class="['msg-row', msg.role]">
            <div class="msg-avatar" :class="msg.role">
              <svg v-if="msg.role==='assistant'" viewBox="0 0 24 24" width="18" height="18">
                <path d="M5.5 8.5a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-9z" fill="#fff"/>
                <line x1="6.5" y1="10.5" x2="17.5" y2="10.5" stroke="#337ecc" stroke-width="0.7" opacity="0.25"/>
                <circle cx="9.5" cy="13.5" r="1.2" fill="#337ecc"/><circle cx="14.5" cy="13.5" r="1.2" fill="#337ecc"/>
                <path d="M10.5 16.5a1.5 1.5 0 0 0 3 0" fill="none" stroke="#337ecc" stroke-width="1" stroke-linecap="round"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="#fff">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="msg-bubble">
              <div class="msg-label">{{ msg.role === 'assistant' ? '小库' : '我' }}</div>
              <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>

          <div v-if="loading" class="msg-row assistant">
            <div class="msg-avatar assistant">
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path d="M5.5 8.5a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-9z" fill="#fff"/>
                <line x1="6.5" y1="10.5" x2="17.5" y2="10.5" stroke="#337ecc" stroke-width="0.7" opacity="0.25"/>
                <circle cx="9.5" cy="13.5" r="1.2" fill="#337ecc"/><circle cx="14.5" cy="13.5" r="1.2" fill="#337ecc"/>
                <path d="M10.5 16.5a1.5 1.5 0 0 0 3 0" fill="none" stroke="#337ecc" stroke-width="1" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="msg-bubble">
              <div class="msg-label">小库</div>
              <span class="thinking-dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="agent-input-area">
        <div class="agent-suggestions">
          <span class="sug" @click="quickQuery('帮我查一下北京仓的库存')">📦 查北京库存</span>
          <span class="sug" @click="quickQuery('FIFO先进先出法是什么')">📖 什么是FIFO</span>
          <span class="sug" @click="quickQuery('如何做采购退货')">🔄 如何退货</span>
          <span class="sug" @click="quickQuery('P001库存够不够20件')">⚠️ 检查缺货</span>
        </div>
        <div class="agent-input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            placeholder="输入指令，小库帮你执行..."
            resize="none"
            @keydown.enter.prevent="sendMessage"
            :disabled="loading"
          />
          <el-button type="primary" :loading="loading" @click="sendMessage" size="large">
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onUnmounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })
function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text)
}

const SESSION_KEY = 'invflow_chat_session_page'
function getOrCreateSessionId() {
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}
const sessionId = ref(getOrCreateSessionId())

const messages = ref([
  { role: 'assistant', content: '你好！我是小库 🤖\n我可以帮你查库存、检查缺货、生成调拨方案、回答业务流程问题。\n有什么需要帮忙的吗？' }
])
const inputText = ref('')
const loading = ref(false)
const msgContainer = ref(null)

function scrollToBottom() {
  nextTick(() => {
    const el = msgContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
watch(messages, scrollToBottom, { deep: true })

async function clearChat() {
  messages.value = [{ role: 'assistant', content: '对话已清空，有需要随时找我！' }]
  const sid = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
  localStorage.setItem(SESSION_KEY, sid)
  sessionId.value = sid
}

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
    messages.value.push({
      role: 'assistant',
      content: res.data.response || '抱歉，处理出错了。'
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

onUnmounted(() => {})
</script>

<style scoped>
.agent-page {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.agent-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

/* 头部 */
.agent-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 24px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}
.agent-title { font-size: 16px; font-weight: 600; color: #303133; }
.agent-subtitle { font-size: 12px; color: #909399; flex: 1; }
.clear-btn { flex-shrink: 0; }

/* 消息区 */
.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f5f7fa;
}
.msg-list { max-width: 800px; margin: 0 auto; }
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.msg-avatar.assistant { background: linear-gradient(135deg,#409EFF,#337ecc); }
.msg-avatar.user { background: #909399; }
.msg-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px; line-height: 1.7;
}
.msg-row.assistant .msg-bubble { background: #fff; border: 1px solid #e4e7ed; border-top-left-radius: 2px; }
.msg-row.user .msg-bubble { background: #409EFF; color: #fff; border-top-right-radius: 2px; }
.msg-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.msg-row.user .msg-label { color: rgba(255,255,255,0.7); text-align: right; }
.msg-text { word-break: break-word; }
.msg-text :deep(table) { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 13px; }
.msg-text :deep(th), .msg-text :deep(td) { border: 1px solid #d0d5dd; padding: 5px 10px; text-align: left; }
.msg-text :deep(th) { background: #f2f3f5; font-weight: 600; }
.msg-text :deep(code) { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.msg-text :deep(pre) { background: #f5f7fa; padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.msg-text :deep(pre code) { background: none; padding: 0; }
.msg-text :deep(ul), .msg-text :deep(ol) { padding-left: 20px; margin: 4px 0; }
.msg-text :deep(li) { margin: 2px 0; }
.msg-text :deep(h1), .msg-text :deep(h2), .msg-text :deep(h3) { font-size: 15px; margin: 10px 0 4px; }
.msg-text :deep(p) { margin: 4px 0; }
.msg-text :deep(a) { color: #409EFF; }
.msg-text :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 8px 0; }

.thinking-dot {
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
.agent-input-area {
  padding: 12px 24px 16px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  flex-shrink: 0;
}
.agent-suggestions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.sug {
  font-size: 12px; color: #409EFF;
  background: #ecf5ff; padding: 4px 12px; border-radius: 14px;
  cursor: pointer; transition: all 0.2s;
}
.sug:hover { background: #409EFF; color: #fff; }
.agent-input-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.agent-input-row :deep(.el-textarea__inner) { font-size: 14px; border-radius: 8px; min-height: 42px; }
.agent-input-row .el-button { height: 42px; padding: 0 24px; }
</style>
