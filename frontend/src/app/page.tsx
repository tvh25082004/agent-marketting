'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatView } from '@/components/Chat/ChatView'
import { AgentFlowView } from '@/components/AgentFlow/AgentFlowView'
import { VideoGallery } from '@/components/Video/VideoGallery'
import { SettingsPanel } from '@/components/Settings/SettingsPanel'
import type { ChatMessage, TaskDetail, VideoInfo, WorkflowStep } from '@/types'
import { sendChatMessage, getTasks, getVideos, pollTaskStatus, checkHealth } from '@/lib/api'

type Tab = 'chat' | 'videos' | 'settings'

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content: '🎵 Chào mừng đến với **Tinasoft-Agentic-Marketing**!\n\nHệ thống AI Agentic sản xuất video nhạc tự động.\n\n**Tôi có thể:**\n- Crawl nhạc từ laomusic.net\n- Lấy lyrics bài hát\n- Tạo giọng ca sĩ nữ AI\n- Làm video studio ánh sáng đẹp\n- Lipsync theo bài hát\n- Chạy lyric karaoke phía dưới\n- Render video 30-60s\n\n💡 **Hãy nhập yêu cầu của bạn!**',
      timestamp: new Date(),
    },
  ])
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentTask, setCurrentTask] = useState<TaskDetail | null>(null)
  const [videos, setVideos] = useState<VideoInfo[]>([])
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([])
  const [systemStatus, setSystemStatus] = useState<string>('checking')

  useEffect(() => {
    checkHealth()
      .then(() => setSystemStatus('online'))
      .catch(() => setSystemStatus('offline'))
    loadVideos()
  }, [])

  const loadVideos = async () => {
    try {
      const data = await getVideos()
      setVideos(data)
    } catch { /* ignore */ }
  }

  const handleSendMessage = async (content: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsProcessing(true)

    const thinkingMsg: ChatMessage = {
      id: `thinking-${Date.now()}`,
      role: 'agent',
      content: '',
      timestamp: new Date(),
      metadata: { status: 'running' },
    }
    setMessages((prev) => [...prev, thinkingMsg])

    try {
      const response = await sendChatMessage(content)
      setWorkflowSteps(['crawl', 'process_audio', 'get_lyrics', 'generate_voice', 'create_video', 'lipsync', 'add_karaoke', 'render'])

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `✅ **Tác vụ đã được khởi tạo!**\n\n**Task ID:** \`${response.taskId}\`\n**Trạng thái:** ${response.status}\n\nHệ thống đang xử lý yêu cầu của bạn. Bạn sẽ nhận được video khi hoàn thành.`,
        timestamp: new Date(),
        taskId: response.taskId,
        metadata: { status: 'running', workflowType: response.workflowType },
      }
      setMessages((prev) => [...prev.filter((m) => m.id !== thinkingMsg.id), assistantMsg])

      pollTaskStatus(response.taskId, (task) => {
        setCurrentTask(task)
        updateWorkflowSteps(task)
        if (task.status === 'completed') {
          setIsProcessing(false)
          loadVideos()
        } else if (task.status === 'failed') {
          setIsProcessing(false)
        }
      })
    } catch (err: unknown) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `❌ **Lỗi:** ${err instanceof Error ? err.message : 'Không thể kết nối đến server'}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev.filter((m) => m.id !== thinkingMsg.id), errorMsg])
      setIsProcessing(false)
    }
  }

  const updateWorkflowSteps = (task: TaskDetail) => {
    const completedSteps = task.steps
      .filter((s) => s.status === 'completed')
      .map((s) => s.stepName as WorkflowStep)
    const currentStep = task.steps.find((s) => s.status === 'running')?.stepName as WorkflowStep | undefined
    const failedStep = task.steps.find((s) => s.status === 'failed')?.stepName as WorkflowStep | undefined

    if (failedStep) {
      setWorkflowSteps((prev) =>
        prev.map((s) => (s === failedStep ? s : s))
      )
    }
    if (currentStep) {
      setWorkflowSteps((prev) =>
        prev.includes(currentStep) ? prev : [...prev, currentStep]
      )
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-16 bg-[#1a202c] border-r border-[#2d3748] flex flex-col items-center py-4 gap-4 flex-shrink-0">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
          TA
        </div>
        <nav className="flex flex-col gap-2 flex-1">
          <button
            onClick={() => setActiveTab('chat')}
            className={`p-2 rounded-lg transition-colors ${activeTab === 'chat' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Chat"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
          </button>
          <button
            onClick={() => setActiveTab('videos')}
            className={`p-2 rounded-lg transition-colors ${activeTab === 'videos' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Videos"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`p-2 rounded-lg transition-colors ${activeTab === 'settings' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Settings"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </button>
        </nav>
        <div className="flex flex-col items-center gap-1">
          <div className={`w-2 h-2 rounded-full ${systemStatus === 'online' ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-[10px] text-gray-500">{systemStatus}</span>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-[#2d3748] flex items-center px-6 bg-[#1a202c]/50 backdrop-blur-sm flex-shrink-0">
          <h1 className="text-lg font-semibold gradient-text">Tinasoft-Agentic-Marketing</h1>
          {isProcessing && (
            <div className="ml-4 flex items-center gap-2 text-sm text-blue-400">
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              <span className="ml-1">Đang xử lý...</span>
            </div>
          )}
        </header>

        <div className="flex-1 flex overflow-hidden">
          <div className={`flex-1 overflow-hidden ${activeTab === 'settings' ? 'hidden' : ''}`}>
            {activeTab === 'chat' && (
              <ChatView
                messages={messages}
                onSend={handleSendMessage}
                isProcessing={isProcessing}
                currentTask={currentTask}
              />
            )}
            {activeTab === 'videos' && (
              <VideoGallery videos={videos} onRefresh={loadVideos} />
            )}
          </div>
          {activeTab === 'settings' && (
            <SettingsPanel />
          )}
          {activeTab !== 'settings' && (
            <AgentFlowView steps={workflowSteps} currentTask={currentTask} />
          )}
        </div>
      </main>
    </div>
  )
}
