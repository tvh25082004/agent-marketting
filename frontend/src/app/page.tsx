'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatView } from '@/components/Chat/ChatView'
import { AgentFlowView } from '@/components/AgentFlow/AgentFlowView'
import { VideoGallery } from '@/components/Video/VideoGallery'
import { SettingsPanel } from '@/components/Settings/SettingsPanel'
import { VideoStudio } from '@/components/Studio/VideoStudio'
import type { ChatMessage, InputAssets, TaskDetail, VideoInfo, WorkflowStep } from '@/types'
import { sendChatMessage, getVideos, pollTaskStatus, checkHealth, getInputAssets } from '@/lib/api'

type Tab = 'chat' | 'studio' | 'videos' | 'settings'

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content: 'Chào mung den voi **Tinasoft AI Video Studio**!\n\n**He thong san xuat video AI:**\n- Face Swap + Lip Sync\n- Thay giao dien + dong bo moi voi audio\n- San xuat hang loat video\n\nChon tab ben trai de bat dau!',
      timestamp: new Date(),
    },
  ])
  const [activeTab, setActiveTab] = useState<Tab>('studio')
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentTask, setCurrentTask] = useState<TaskDetail | null>(null)
  const [videos, setVideos] = useState<VideoInfo[]>([])
  const [assets, setAssets] = useState<InputAssets | null>(null)
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([])
  const [systemStatus, setSystemStatus] = useState<string>('checking')

  useEffect(() => {
    checkHealth()
      .then(() => setSystemStatus('online'))
      .catch(() => setSystemStatus('offline'))
    loadVideos()
    loadAssets()
  }, [])

  const loadVideos = async () => {
    try {
      const data = await getVideos()
      setVideos(data)
    } catch { /* ignore */ }
  }

  const loadAssets = async () => {
    try {
      setAssets(await getInputAssets())
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
        content: `✅ **Tac vu da duoc khoi tao!**\n\n**Task ID:** \`${response.taskId}\`\n**Trang thai:** ${response.status}\n\nHe thong dang xu ly. Ban se nhan duoc video khi hoan thanh.`,
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
          const videoUrl = task.outputData?.video_url || task.outputData?.videoUrl
          if (typeof videoUrl === 'string' && videoUrl) {
            setMessages((prev) => [
              ...prev,
              {
                id: `completed-${Date.now()}`,
                role: 'assistant',
                content: `✅ **Video output da xong!**\n\nLink: ${videoUrl}\n\nXem tab Videos hoac tai truc tiep.`,
                timestamp: new Date(),
                taskId: task.taskId,
                metadata: { status: 'completed', videoUrl },
              },
            ])
          }
          loadVideos()
        } else if (task.status === 'failed') {
          setIsProcessing(false)
        }
      })
    } catch (err: unknown) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `❌ **Loi:** ${err instanceof Error ? err.message : 'Khong the ket noi den server'}`,
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

  const tabIcon = (tab: Tab) => {
    switch (tab) {
      case 'studio':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )
      case 'chat':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )
      case 'videos':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        )
      case 'settings':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        )
    }
  }

  const tabLabel = (tab: Tab) => {
    switch (tab) {
      case 'studio': return 'Studio'
      case 'chat': return 'Chat AI'
      case 'videos': return 'Videos'
      case 'settings': return 'Settings'
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 bg-[#1a202c] border-r border-[#2d3748] flex flex-col items-center py-4 gap-3 flex-shrink-0">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
          AI
        </div>
        <nav className="flex flex-col gap-1 flex-1">
          {(['studio', 'chat', 'videos', 'settings'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`p-2 rounded-lg transition-colors relative group ${
                activeTab === tab ? 'bg-purple-500/20 text-purple-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
              title={tabLabel(tab)}
            >
              {tabIcon(tab)}
              <span className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-xs text-gray-200 rounded-md opacity-0 group-hover:opacity-100 whitespace-nowrap z-50 pointer-events-none transition-opacity">
                {tabLabel(tab)}
              </span>
            </button>
          ))}
        </nav>
        <div className="flex flex-col items-center gap-1">
          <div className={`w-2 h-2 rounded-full ${systemStatus === 'online' ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-[10px] text-gray-500">{systemStatus}</span>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-[#2d3748] flex items-center px-6 bg-[#1a202c]/50 backdrop-blur-sm flex-shrink-0">
          <h1 className="text-lg font-semibold gradient-text">Tinasoft AI Video Studio</h1>
          {isProcessing && (
            <div className="ml-4 flex items-center gap-2 text-sm text-blue-400">
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              <span className="ml-1">Dang xu ly...</span>
            </div>
          )}
        </header>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {activeTab === 'studio' && (
              <VideoStudio />
            )}
            {activeTab === 'chat' && (
              <ChatView
                messages={messages}
                onSend={handleSendMessage}
                isProcessing={isProcessing}
                currentTask={currentTask}
                assets={assets}
              />
            )}
            {activeTab === 'videos' && (
              <VideoGallery videos={videos} onRefresh={loadVideos} />
            )}
            {activeTab === 'settings' && (
              <div className="flex h-full">
                <div className="flex-1 overflow-y-auto">
                  <SettingsPanel />
                </div>
              </div>
            )}
          </div>
          {activeTab !== 'settings' && activeTab !== 'studio' && (
            <AgentFlowView steps={workflowSteps} currentTask={currentTask} />
          )}
        </div>
      </main>
    </div>
  )
}
