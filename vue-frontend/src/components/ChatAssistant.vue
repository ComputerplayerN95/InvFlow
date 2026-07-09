<template>
  <div class="chat-assistant">
    <!-- 浮动按钮 -->
    <div class="float-btn" @click="togglePanel" :class="{ active: visible }">
      <svg v-if="!visible" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2a10 10 0 0 1 10 10c0 3.5-2 6.5-5 8l-3 2v-2.5A10 10 0 0 1 12 2z"/>
        <path d="M8 10h8M8 14h5"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </div>

    <!-- 聊天面板 -->
    <transition name="slide">
      <div v-if="visible" class="chat-panel">
        <div class="chat-header">
          <div class="header-info">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#409EFF">
              <path d="M12 2a10 10 0 0 1 10 10c0 3.5-2 6.5-5 8l-3 2v-2.5A10 10 0 0 1 12 2z"/>
            </svg>
            <span>小库 AI 助手</span>
          </div>
          <div class="header-actions">
            <el-tooltip content="清空对话" placement="bottom">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" class="header-icon" @click="clearChat">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </el-tooltip>
          </div>
        </div>

        <div class="chat-messages" ref="msgContainer">
          <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
            <div class="avatar" :class="msg.role">
              <svg v-if="msg.role==='assistant'" viewBox="0 0 24 24" width="16" height="16" fill="#fff">
                <path d="M12 2a10 10 0 0 1 10 10c0 3.5-2 6.5-5 8l-3 2v-2.5A10 10 0 0 1 12 2z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="#fff">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="bubble">
              <div class="bubble-text" style="white-space:pre-wrap">{{ msg.content }}</div>
              <div v-if="msg.toolResult" class="tool-result">
                <el-tag size="small" type="success" effect="plain" v-if="msg.toolResult.success">✅ 操作成功</el-tag>
                <el-tag size="small" type="danger" effect="plain" v-else>❌ 操作失败</el-tag>
              </div>
            </div>
          </div>
          <div v-if="loading" class="message assistant">
            <div class="avatar assistant">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="#fff">
                <path d="M12 2a10 10 0 0 1 10 10c0 3.5-2 6.5-5 8l-3 2v-2.5A10 10 0 0 1 12 2z"/>
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
import { ref, nextTick, watch } from 'vue'
import axios from 'axios'

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

function clearChat() {
  messages.value = [
    { role: 'assistant', content: '对话已清空，有需要随时找我！' }
  ]
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
      role: m.role,
      content: m.content
    }))

    const res = await axios.post('/api/agent/chat', {
      message: text,
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
</script>

<style scoped>
.chat-assistant { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

/* 浮动按钮 */
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
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(64,158,255,0.4);
  z-index: 9999;
  transition: all 0.3s ease;
}
.float-btn:hover { transform: scale(1.08); box-shadow: 0 6px 20px rgba(64,158,255,0.5); }
.float-btn.active { background: #F56C6C; }

/* 聊天面板 */
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

.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(20px); }

/* 头部 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: #fff;
}
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
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar.assistant { background: #409EFF; }
.avatar.user { background: #909399; }

.bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
}
.message.assistant .bubble { background: #fff; border: 1px solid #e4e7ed; border-top-left-radius: 2px; }
.message.user .bubble { background: #409EFF; color: #fff; border-top-right-radius: 2px; }

.bubble-text { word-break: break-word; }
.tool-result { margin-top: 8px; }

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
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.chat-input :deep(.el-textarea__inner) { font-size: 13px; border-radius: 8px; }
.send-btn { flex-shrink: 0; margin-top: 0; }

/* 快捷建议 */
.chat-footer {
  padding: 8px 12px 10px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.suggestion {
  font-size: 12px;
  color: #409EFF;
  background: #ecf5ff;
  padding: 3px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.suggestion:hover { background: #409EFF; color: #fff; }
</style>
