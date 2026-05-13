'use client'

import { useState, useRef, useEffect } from 'react'
import type { ReactNode } from 'react'
import { Image, Mic2, Play, Sparkles, Wand2, Bot } from 'lucide-react'
import type { ChatMessage, InputAssets, TaskDetail } from '@/types'

interface ChatViewProps {
  messages: ChatMessage[]
  onSend: (message: string) => void
  isProcessing: boolean
  currentTask: TaskDetail | null
  assets: InputAssets | null
}

export function ChatView({ messages, onSend, isProcessing, currentTask, assets }: ChatViewProps) {
  const [input, setInput] = useState('')
  const [audioPath, setAudioPath] = useState('')
  const [imagePath, setImagePath] = useState('')
  const [videoPath, setVideoPath] = useState('')
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

  useEffect(() => {
    if (!assets) return
    if (assets.audio.length > 0 && !assets.audio.some((a) => a.path === audioPath)) {
      setAudioPath(assets.audio[0].path)
    }
    if (assets.images.length > 0 && !assets.images.some((i) => i.path === imagePath)) {
      setImagePath(assets.images[0].path)
    }
    if (assets.videos.length > 0 && !assets.videos.some((v) => v.path === videoPath)) {
      setVideoPath(assets.videos[0].path)
    }
  }, [assets])

  const buildPrompt = () => {
    const prompt = [
      'AI Dancing theo flow aidancing.net:',
      `audio_path=${audioPath}`,
      `image_path=${imagePath}`,
      `reference_video=${videoPath}`,
      'Tao video face-swap + lip-sync tu anh ca si, audio nhac va video mau trong thu muc input. Output MP4.',
    ].join('\n')
    setInput(prompt)
    inputRef.current?.focus()
  }

  const runDirect = () => {
    const prompt = [
      'AI Dancing aidancing input/',
      `Dung audio ${audioPath}`,
      `Dung anh ${imagePath}`,
      `Dung video mau ${videoPath}`,
      'Render video output hoan chinh.',
    ].join('\n')
    onSend(prompt)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-[#2d3748] bg-[#111827] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-100">
              <Bot className="h-4 w-4 text-purple-400" />
              AI Agent Chat
            </div>
            <p className="mt-1 text-xs text-gray-400">Nhap yeu cau, he thong se tu dong xu ly pipeline.</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={buildPrompt}
              disabled={isProcessing}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-[#334155] px-3 text-xs text-gray-200 hover:border-purple-400/70 hover:bg-purple-400/10 disabled:opacity-50"
            >
              <Wand2 className="h-4 w-4" />
              Dien prompt
            </button>
            <button
              type="button"
              onClick={runDirect}
              disabled={isProcessing}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-purple-500 px-3 text-xs font-semibold text-white hover:bg-purple-400 disabled:bg-gray-700 disabled:text-gray-500"
            >
              <Play className="h-4 w-4" />
              Chay
            </button>
          </div>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <AssetSelect icon={<Mic2 className="h-4 w-4" />} label="Audio" value={audioPath} onChange={setAudioPath} options={assets?.audio || []} />
          <AssetSelect icon={<Image className="h-4 w-4" />} label="Anh goc" value={imagePath} onChange={setImagePath} options={assets?.images || []} />
          <AssetSelect icon={<Play className="h-4 w-4" />} label="Video mau" value={videoPath} onChange={setVideoPath} options={assets?.videos || []} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-purple-500 text-white rounded-br-md'
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
            <div className="text-xs text-purple-400 font-medium mb-1">Agent Status</div>
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
            placeholder={isProcessing ? 'He thong dang xu ly...' : 'Nhap yeu cau cua ban...'}
            disabled={isProcessing}
            rows={1}
            className="flex-1 bg-[#2d3748] rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-purple-500/50 resize-none disabled:opacity-50 placeholder-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="px-5 py-3 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
            Gui
          </button>
        </div>
        <div className="mt-2 text-[10px] text-gray-500 px-1">
          Enter de gui - Shift+Enter de xuong dong
        </div>
      </form>
    </div>
  )
}

function AssetSelect({
  icon,
  label,
  value,
  onChange,
  options,
}: {
  icon: ReactNode
  label: string
  value: string
  onChange: (value: string) => void
  options: { name: string; path: string }[]
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-gray-400">
        {icon}
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-md border border-[#334155] bg-[#1f2937] px-2 text-xs text-gray-100 outline-none focus:border-purple-400"
      >
        {options.length === 0 ? (
          <option value="">No files</option>
        ) : (
          options.map((asset) => (
            <option key={asset.path} value={asset.path}>
              {asset.name}
            </option>
          ))
        )}
      </select>
    </label>
  )
}

function renderMessageContent(msg: ChatMessage) {
  if (msg.role === 'user') {
    return msg.content
  }

  const lines = msg.content.split('\n')
  return lines.map((line, i) => {
    if (line.startsWith('## ')) {
      return <h2 key={i} className="text-purple-300 font-semibold text-base mt-2 mb-1">{line.slice(3)}</h2>
    }
    if (line.startsWith('**') && line.endsWith('**')) {
      return <strong key={i} className="text-purple-200">{line.slice(2, -2)}</strong>
    }
    if (line.startsWith('- ')) {
      return <div key={i} className="flex gap-2 ml-2"><span className="text-purple-400">•</span><span>{line.slice(2)}</span></div>
    }
    if (line.startsWith('```')) {
      return <code key={i} className="block bg-black/30 rounded-lg px-3 py-2 text-xs font-mono my-1">{line.replace(/```/g, '')}</code>
    }
    if (line.startsWith('Link: ')) {
      const href = line.slice(6).trim()
      return (
        <a key={i} href={href} target="_blank" rel="noreferrer" className="font-medium text-purple-300 underline underline-offset-4">
          {href}
        </a>
      )
    }
    return <span key={i}>{line}{i < lines.length - 1 ? <br /> : null}</span>
  })
}
