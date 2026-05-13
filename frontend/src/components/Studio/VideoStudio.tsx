'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Upload,
  Image,
  Music,
  Video,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  Sparkles,
  ChevronDown,
  FileUp,
} from 'lucide-react'
import type {
  InputAssets,
  InputAsset,
  ProcessResponse,
  BatchProcessResponse,
  BatchJobResult,
} from '@/types'
import {
  uploadImage,
  uploadAudio,
  uploadVideo,
  directProcess,
  batchProcess,
  getInputAssets,
  pollTaskStatus,
} from '@/lib/api'
import type { TaskDetail } from '@/types'

type ProcessStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'

interface ProcessJob {
  id: string
  audioName: string
  status: ProcessStatus
  videoUrl?: string
  message?: string
}

export function VideoStudio() {
  const [assets, setAssets] = useState<InputAssets | null>(null)
  const [selectedImage, setSelectedImage] = useState('')
  const [selectedVideo, setSelectedVideo] = useState('')
  const [selectedAudio, setSelectedAudio] = useState('')
  const [status, setStatus] = useState<ProcessStatus>('idle')
  const [statusMessage, setStatusMessage] = useState('')
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [batchMode, setBatchMode] = useState(false)
  const [batchJobs, setBatchJobs] = useState<ProcessJob[]>([])
  const [expanded, setExpanded] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState<string | null>(null)

  const loadAssets = async () => {
    try {
      const data = await getInputAssets()
      setAssets(data)
      if (data.images.length > 0 && !selectedImage) setSelectedImage(data.images[0].path)
      if (data.videos.length > 0 && !selectedVideo) setSelectedVideo(data.videos[0].path)
      if (data.audio.length > 0 && !selectedAudio) setSelectedAudio(data.audio[0].path)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadAssets() }, [])

  const handleFileUpload = async (type: 'image' | 'audio' | 'video', file: File) => {
    setUploading(type)
    setStatusMessage(`Uploading ${file.name}...`)
    try {
      let result
      if (type === 'image') result = await uploadImage(file)
      else if (type === 'audio') result = await uploadAudio(file)
      else result = await uploadVideo(file)

      await loadAssets()
      if (type === 'image') setSelectedImage(result.path)
      else if (type === 'audio') setSelectedAudio(result.path)
      else setSelectedVideo(result.path)
      setStatusMessage(`Uploaded: ${file.name}`)
    } catch (e) {
      setStatusMessage(`Upload failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    }
    setUploading(null)
  }

  const triggerFileInput = (type: 'image' | 'audio' | 'video') => {
    const input = document.createElement('input')
    input.type = 'file'
    const acceptMap = { image: 'image/*', audio: 'audio/*', video: 'video/*' }
    input.accept = acceptMap[type]
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) handleFileUpload(type, file)
    }
    input.click()
  }

  const runProcess = async () => {
    if (!selectedImage || !selectedVideo || (!selectedAudio && !batchMode)) return
    setStatus('processing')
    setResultUrl(null)

    if (batchMode) {
      setStatusMessage('Starting batch process...')
      try {
        const result: BatchProcessResponse = await batchProcess(selectedImage, selectedVideo)
        setBatchJobs(result.results.map(r => ({
          id: r.audioName,
          audioName: r.audioName,
          status: r.status === 'completed' ? 'completed' : 'failed',
          videoUrl: r.videoUrl,
        })))
        const successCount = result.results.filter(r => r.status === 'completed').length
        setStatus('completed')
        setStatusMessage(`Batch complete: ${successCount}/${result.total} success`)
        await loadAssets()
      } catch (e) {
        setStatus('failed')
        setStatusMessage(`Batch failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
      }
      return
    }

    setStatusMessage('Processing face swap + lip sync...')
    try {
      const result: ProcessResponse = await directProcess(selectedImage, selectedVideo, selectedAudio)
      if (result.status === 'completed' && result.videoUrl) {
        setStatus('completed')
        setResultUrl(result.videoUrl)
        setStatusMessage('Video created successfully!')
        await loadAssets()
      } else {
        setStatus('failed')
        setStatusMessage(result.message || 'Processing failed')
      }
    } catch (e) {
      setStatus('failed')
      setStatusMessage(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`)
    }
  }

  const selectFromAssets = (type: 'images' | 'videos' | 'audio', path: string) => {
    if (type === 'images') setSelectedImage(path)
    else if (type === 'videos') setSelectedVideo(path)
    else setSelectedAudio(path)
  }

  const renderAssetSelector = (
    label: string,
    icon: React.ReactNode,
    items: InputAsset[],
    selected: string,
    onSelect: (path: string) => void,
    onUpload: () => void,
    accent: string,
  ) => (
    <div className="bg-[#1a2332] rounded-xl border border-[#2d3a4e] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2d3a4e]">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-gray-200">{label}</span>
        </div>
        <button
          onClick={onUpload}
          disabled={uploading !== null}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-[#2d3a4e] text-gray-300 hover:bg-[#3d4a5e] disabled:opacity-50 transition-colors"
        >
          <FileUp className="w-3.5 h-3.5" />
          Upload
        </button>
      </div>
      <div className="p-2">
        {items.length === 0 ? (
          <div className="text-center py-6 text-gray-500 text-xs">
            <div className="mb-2">
              {icon}
            </div>
            No files yet. Upload one above.
          </div>
        ) : (
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {items.map((item) => (
              <button
                key={item.path}
                onClick={() => onSelect(item.path)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  selected === item.path
                    ? `bg-${accent}-500/20 text-${accent}-300 border border-${accent}-500/30`
                    : 'text-gray-400 hover:bg-[#253040] border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate max-w-[180px]">{item.name}</span>
                  <span className="text-[10px] text-gray-500 shrink-0 ml-2">
                    {(item.size / 1024 / 1024).toFixed(1)}MB
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-[#2d3748] bg-[#111827] px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Video Production Studio</h2>
              <p className="text-xs text-gray-400 mt-0.5">Face Swap + Lip Sync + Audio Replacement</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={batchMode}
                onChange={(e) => setBatchMode(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800"
              />
              <Layers className="w-4 h-4" />
              Batch Mode (all audios)
            </label>
            <button
              onClick={runProcess}
              disabled={status === 'processing' || !selectedImage || !selectedVideo || (!selectedAudio && !batchMode)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                status === 'processing'
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-400 hover:to-pink-400 shadow-lg shadow-purple-500/25'
              }`}
            >
              {status === 'processing' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {status === 'processing' ? 'Processing...' : batchMode ? 'Run Batch' : 'Generate Video'}
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Asset Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {renderAssetSelector(
            'Source Image',
            <Image className="w-4 h-4 text-pink-400" />,
            assets?.images || [],
            selectedImage,
            (p) => selectFromAssets('images', p),
            () => triggerFileInput('image'),
            'pink',
          )}
          {renderAssetSelector(
            'Reference Video',
            <Video className="w-4 h-4 text-blue-400" />,
            assets?.videos || [],
            selectedVideo,
            (p) => selectFromAssets('videos', p),
            () => triggerFileInput('video'),
            'blue',
          )}
          {renderAssetSelector(
            'Audio Track',
            <Music className="w-4 h-4 text-green-400" />,
            assets?.audio || [],
            selectedAudio,
            (p) => selectFromAssets('audio', p),
            () => triggerFileInput('audio'),
            'green',
          )}
        </div>

        {/* Status */}
        {status !== 'idle' && (
          <div className={`rounded-xl border p-4 ${
            status === 'processing' ? 'bg-blue-500/5 border-blue-500/30' :
            status === 'completed' ? 'bg-green-500/5 border-green-500/30' :
            status === 'failed' ? 'bg-red-500/5 border-red-500/30' :
            'bg-gray-800 border-gray-700'
          }`}>
            <div className="flex items-center gap-3">
              {status === 'processing' && <Loader2 className="w-5 h-5 animate-spin text-blue-400" />}
              {status === 'completed' && <CheckCircle2 className="w-5 h-5 text-green-400" />}
              {status === 'failed' && <XCircle className="w-5 h-5 text-red-400" />}
              <span className={`text-sm ${
                status === 'processing' ? 'text-blue-300' :
                status === 'completed' ? 'text-green-300' :
                status === 'failed' ? 'text-red-300' : 'text-gray-300'
              }`}>
                {statusMessage}
              </span>
            </div>

            {/* Batch results */}
            {batchMode && batchJobs.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="text-xs font-medium text-gray-400 mb-2">Batch Results:</div>
                {batchJobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between bg-[#1a2332] rounded-lg px-4 py-2.5">
                    <div className="flex items-center gap-3">
                      {job.status === 'completed' ? (
                        <CheckCircle2 className="w-4 h-4 text-green-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-sm text-gray-300">{job.audioName}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {job.videoUrl && (
                        <a
                          href={job.videoUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-blue-400 hover:text-blue-300 underline"
                        >
                          View Video
                        </a>
                      )}
                      <span className={`text-xs ${job.status === 'completed' ? 'text-green-400' : 'text-red-400'}`}>
                        {job.status === 'completed' ? 'OK' : 'FAIL'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Single result */}
            {!batchMode && resultUrl && (
              <div className="mt-4">
                <video
                  src={resultUrl}
                  controls
                  className="w-full max-w-lg rounded-lg border border-green-500/30"
                  style={{ maxHeight: '300px' }}
                />
                <div className="mt-2 flex gap-2">
                  <a
                    href={resultUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 underline"
                  >
                    Open in new tab
                  </a>
                  <a
                    href={resultUrl}
                    download
                    className="text-xs text-green-400 hover:text-green-300 underline"
                  >
                    Download
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Pipeline info */}
        <details className="bg-[#1a2332] rounded-xl border border-[#2d3a4e]">
          <summary className="px-4 py-3 cursor-pointer text-sm text-gray-300 font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            How it works
            <ChevronDown className="w-3.5 h-3.5 ml-auto" />
          </summary>
          <div className="px-4 pb-4 space-y-2 text-xs text-gray-400">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-pink-500/20 text-pink-400 flex items-center justify-center shrink-0 text-xs font-bold">1</div>
              <div><strong className="text-gray-300">Face Swap</strong> - InsightFace thay khuôn mặt từ ảnh nguồn vào từng frame video</div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center shrink-0 text-xs font-bold">2</div>
              <div><strong className="text-gray-300">Lip Sync</strong> - Đồng bộ khớp môi theo audio mục tiêu (amplitude-based)</div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center shrink-0 text-xs font-bold">3</div>
              <div><strong className="text-gray-300">Audio</strong> - Ghép audio sạch vào video output</div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 text-xs font-bold">4</div>
              <div><strong className="text-gray-300">Batch</strong> - Tự động xử lý tất cả audio trong input/ với cùng 1 video + image</div>
            </div>
          </div>
        </details>
      </div>
    </div>
  )
}
