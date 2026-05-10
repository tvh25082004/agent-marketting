export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'agent'
  content: string
  timestamp: Date
  taskId?: string
  metadata?: {
    workflowType?: string
    currentStep?: string
    status?: string
    videoUrl?: string
    tokensUsed?: number
    totalCost?: number
  }
}

export interface TaskStatus {
  taskId: string
  status: string
  workflowType: string
  currentStep?: string
  progress?: number
  errorMessage?: string
  startedAt?: string
  completedAt?: string
  videoUrl?: string
}

export interface AgentStep {
  stepName: string
  agentName: string
  status: string
  tokensUsed: number
  modelUsed?: string
  startedAt?: string
  completedAt?: string
}

export interface TaskDetail {
  taskId: string
  workflowType: string
  status: string
  inputData?: Record<string, unknown>
  outputData?: Record<string, unknown>
  tokensUsed: number
  totalCost: number
  modelUsed?: string
  steps: AgentStep[]
  createdAt?: string
}

export interface VideoInfo {
  id: number
  title: string
  videoPath: string
  videoUrl?: string
  thumbnailPath?: string
  durationSeconds?: number
  status: string
  feedbackScore?: number
  createdAt?: string
}

export interface ScheduleConfig {
  enabled: boolean
  intervalMinutes: number
  maxSongs: number
  model?: string
}

export interface ModelInfo {
  name: string
  type?: string
  provider?: string
}

export interface FeedbackData {
  taskId?: string
  videoId?: number
  score: number
  feedbackText?: string
}

export type WorkflowStep =
  | 'crawl'
  | 'process_audio'
  | 'get_lyrics'
  | 'generate_voice'
  | 'create_video'
  | 'lipsync'
  | 'add_karaoke'
  | 'render'
  | 'completed'
  | 'failed'

export const STEP_LABELS: Record<WorkflowStep, string> = {
  crawl: 'Crawl nhạc từ laomusic.net',
  process_audio: 'Xử lý âm thanh',
  get_lyrics: 'Lấy lyrics bài hát',
  generate_voice: 'Tạo giọng ca sĩ nữ AI',
  create_video: 'Tạo video studio ánh sáng',
  lipsync: 'Đồng bộ khớp miệng',
  add_karaoke: 'Thêm lyric karaoke',
  render: 'Render video hoàn chỉnh',
  completed: 'Hoàn thành',
  failed: 'Thất bại',
}

export const STEP_ICONS: Record<WorkflowStep, string> = {
  crawl: 'download',
  process_audio: 'music',
  get_lyrics: 'file-text',
  generate_voice: 'mic',
  create_video: 'film',
  lipsync: 'user',
  add_karaoke: 'subtitles',
  render: 'clapperboard',
  completed: 'check-circle',
  failed: 'x-circle',
}
