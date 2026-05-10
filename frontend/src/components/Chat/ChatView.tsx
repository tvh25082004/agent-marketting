'use client'

import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, TaskDetail } from '@/types'

interface ChatViewProps {
  messages: ChatMessage[]
  onSend: (message: string) => void
  isProcessing: boolean
  currentTask: TaskDetail | null
}

export function ChatView({ messages, onSend, isProcessing, currentTask }: ChatViewProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isProcessing) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-md'
                  : msg.role === 'system'
                  ? 'agent-bg rounded-bl-md'
                  : msg.role === 'agent'
                  ? 'bg-[#2d3748] rounded-bl-md'
                  : 'bg-gray-800 rounded-bl-md'
              }`}
            >
              <div className="text-sm leading-relaxed whitespace-pre-wrap">
                {renderMessageContent(msg)}
              </div>
              <div className="text-[10px] mt-1 opacity-50">
                {msg.timestamp.toLocaleTimeString('vi-VN')}
              </div>
            </div>
          </div>
        ))}

        {currentTask && currentTask.status === 'running' && (
          <div className="agent-bg rounded-2xl px-4 py-3 max-w-[80%]">
            <div className="text-xs text-blue-400 font-medium mb-1">Agent Status</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <span className="text-gray-400">Tokens:</span>
              <span className="text-gray-200">{currentTask.tokensUsed || 0}</span>
              <span className="text-gray-400">Cost:</span>
              <span className="text-gray-200">${(currentTask.totalCost || 0).toFixed(4)}</span>
              <span className="text-gray-400">Model:</span>
              <span className="text-gray-200">{currentTask.modelUsed || 'N/A'}</span>
              <span className="text-gray-400">Steps:</span>
              <span className="text-gray-200">{currentTask.steps?.length || 0}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-[#2d3748] bg-[#1a202c]/50">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isProcessing ? 'Hệ thống đang xử lý...' : 'Nhập yêu cầu của bạn...'}
            disabled={isProcessing}
            rows={1}
            className="flex-1 bg-[#2d3748] rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500/50 resize-none disabled:opacity-50 placeholder-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="px-5 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
            Gửi
          </button>
        </div>
        <div className="mt-2 text-[10px] text-gray-500 px-1">
          Enter để gửi · Shift+Enter để xuống dòng
        </div>
      </form>
    </div>
  )
}

function renderMessageContent(msg: ChatMessage) {
  if (msg.role === 'user') {
    return msg.content
  }

  const lines = msg.content.split('\n')
  return lines.map((line, i) => {
    if (line.startsWith('## ')) {
      return <h2 key={i} className="text-blue-300 font-semibold text-base mt-2 mb-1">{line.slice(3)}</h2>
    }
    if (line.startsWith('**') && line.endsWith('**')) {
      return <strong key={i} className="text-blue-200">{line.slice(2, -2)}</strong>
    }
    if (line.startsWith('- ')) {
      return <div key={i} className="flex gap-2 ml-2"><span className="text-blue-400">•</span><span>{line.slice(2)}</span></div>
    }
    if (line.startsWith('```')) {
      return <code key={i} className="block bg-black/30 rounded-lg px-3 py-2 text-xs font-mono my-1">{line.replace(/```/g, '')}</code>
    }
    return <span key={i}>{line}{i < lines.length - 1 ? <br /> : null}</span>
  })
}
