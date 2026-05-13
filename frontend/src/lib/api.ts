import type {
  ChatMessage,
  TaskStatus,
  TaskDetail,
  VideoInfo,
  ScheduleConfig,
  FeedbackData,
  InputAssets,
  UploadResponse,
  ProcessResponse,
  BatchProcessResponse,
} from '@/types'

const API_BASE = '/api'

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `API error: ${res.status}`)
  }
  return res.json()
}

function mapTaskStatus(raw: Record<string, unknown>): TaskStatus {
  return {
    taskId: (raw.task_id ?? raw.taskId) as string,
    status: raw.status as string,
    workflowType: (raw.workflow_type ?? raw.workflowType ?? 'music_video') as string,
    currentStep: (raw.current_step ?? raw.currentStep) as string | undefined,
    progress: raw.progress as number | undefined,
    errorMessage: (raw.error_message ?? raw.errorMessage) as string | undefined,
    startedAt: (raw.started_at ?? raw.startedAt) as string | undefined,
    completedAt: (raw.completed_at ?? raw.completedAt) as string | undefined,
    videoUrl: (raw.video_url ?? raw.videoUrl) as string | undefined,
  }
}

function mapTaskDetail(raw: Record<string, unknown>): TaskDetail {
  const rawSteps = (raw.steps ?? []) as Record<string, unknown>[]
  return {
    taskId: (raw.task_id ?? raw.taskId) as string,
    workflowType: (raw.workflow_type ?? raw.workflowType ?? 'music_video') as string,
    status: raw.status as string,
    inputData: raw.input_data as Record<string, unknown> | undefined,
    outputData: raw.output_data as Record<string, unknown> | undefined,
    tokensUsed: (raw.tokens_used ?? raw.tokensUsed ?? 0) as number,
    totalCost: (raw.total_cost ?? raw.totalCost ?? 0) as number,
    modelUsed: (raw.model_used ?? raw.modelUsed) as string | undefined,
    steps: rawSteps.map((s) => ({
      stepName: (s.step_name ?? s.stepName) as string,
      agentName: (s.agent_name ?? s.agentName) as string,
      status: s.status as string,
      tokensUsed: (s.tokens_used ?? s.tokensUsed ?? 0) as number,
      modelUsed: (s.model_used ?? s.modelUsed) as string | undefined,
      startedAt: (s.started_at ?? s.startedAt) as string | undefined,
      completedAt: (s.completed_at ?? s.completedAt) as string | undefined,
    })),
    createdAt: (raw.created_at ?? raw.createdAt) as string | undefined,
  }
}

function mapVideoInfo(raw: Record<string, unknown>): VideoInfo {
  return {
    id: raw.id as number,
    title: raw.title as string,
    videoPath: (raw.video_path ?? raw.videoPath) as string,
    videoUrl: (raw.video_url ?? raw.videoUrl) as string | undefined,
    thumbnailPath: (raw.thumbnail_path ?? raw.thumbnailPath) as string | undefined,
    durationSeconds: (raw.duration_seconds ?? raw.durationSeconds) as number | undefined,
    status: raw.status as string,
    feedbackScore: (raw.feedback_score ?? raw.feedbackScore) as number | undefined,
    createdAt: (raw.created_at ?? raw.createdAt) as string | undefined,
  }
}

export async function sendChatMessage(
  message: string,
  model?: string,
  schedule?: boolean,
): Promise<{ taskId: string; status: string; message: string; workflowType: string }> {
  const raw = await fetchApi<Record<string, unknown>>('/agents/chat', {
    method: 'POST',
    body: JSON.stringify({ message, model, schedule, intervalMinutes: 2 }),
  })
  return {
    taskId: (raw.task_id ?? raw.taskId ?? '') as string,
    status: (raw.status ?? 'running') as string,
    message: (raw.message ?? '') as string,
    workflowType: (raw.workflow_type ?? raw.workflowType ?? 'music_video') as string,
  }
}

export async function getTasks(): Promise<TaskStatus[]> {
  const raw = await fetchApi<Record<string, unknown>[]>('/agents/tasks')
  return raw.map(mapTaskStatus)
}

export async function getTaskDetail(taskId: string): Promise<TaskDetail> {
  const raw = await fetchApi<Record<string, unknown>>(`/agents/tasks/${taskId}`)
  return mapTaskDetail(raw)
}

export async function getVideos(): Promise<VideoInfo[]> {
  const raw = await fetchApi<Record<string, unknown>[]>('/agents/videos')
  return raw.map(mapVideoInfo)
}

export async function getInputAssets(): Promise<InputAssets> {
  return fetchApi('/agents/assets')
}

export async function getSchedule(): Promise<{ enabled: boolean; jobs: unknown[] }> {
  return fetchApi('/schedule')
}

export async function updateSchedule(config: ScheduleConfig): Promise<{ status: string; message: string }> {
  return fetchApi('/schedule', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

export async function deleteSchedule(): Promise<{ status: string; message: string }> {
  return fetchApi('/schedule', { method: 'DELETE' })
}

export async function submitFeedback(feedback: FeedbackData): Promise<{ status: string; score: number }> {
  return fetchApi('/feedback', {
    method: 'POST',
    body: JSON.stringify(feedback),
  })
}

export async function getModels(): Promise<{ models: string[]; default: string }> {
  return fetchApi('/models')
}

export async function checkHealth(): Promise<{ status: string; app: string; version: string }> {
  return fetchApi('/health')
}

export async function pollTaskStatus(taskId: string, onUpdate: (task: TaskDetail) => void): Promise<void> {
  const poll = async () => {
    try {
      const task = await getTaskDetail(taskId)
      onUpdate(task)
      if (task.status === 'running' || task.status === 'pending') {
        setTimeout(poll, 2000)
      }
    } catch {
      setTimeout(poll, 5000)
    }
  }
  poll()
}

// ── Upload API ─────────────────────────────────────────────────────

export async function uploadImage(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/agents/upload/image`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/agents/upload/audio`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/agents/upload/video`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

// ── Direct Process API ─────────────────────────────────────────────

export async function directProcess(
  imagePath: string,
  videoPath: string,
  audioPath: string,
): Promise<ProcessResponse> {
  return fetchApi('/agents/process', {
    method: 'POST',
    body: JSON.stringify({
      image_path: imagePath,
      video_path: videoPath,
      audio_path: audioPath,
    }),
  })
}

export async function batchProcess(
  imagePath: string,
  videoPath: string,
): Promise<BatchProcessResponse> {
  const form = new FormData()
  form.append('image_path', imagePath)
  form.append('video_path', videoPath)
  const res = await fetch(`${API_BASE}/agents/batch`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Batch failed: ${res.status}`)
  return res.json()
}
