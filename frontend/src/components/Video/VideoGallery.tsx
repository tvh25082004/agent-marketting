'use client'

import { useState } from 'react'
import type { VideoInfo } from '@/types'

interface VideoGalleryProps {
  videos: VideoInfo[]
  onRefresh: () => void
}

export function VideoGallery({ videos, onRefresh }: VideoGalleryProps) {
  const [selectedVideo, setSelectedVideo] = useState<VideoInfo | null>(null)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-[#2d3748]">
        <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          Video Gallery
          <span className="text-gray-500 font-normal">({videos.length})</span>
        </h2>
        <button
          onClick={onRefresh}
          className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
          title="Refresh"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <svg className="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            <p className="text-sm">Chưa có video nào</p>
            <p className="text-xs mt-1 text-gray-600">Gửi yêu cầu để tạo video đầu tiên</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {videos.map((video) => (
              <div
                key={video.id}
                className="group bg-[#1a202c] rounded-xl border border-[#2d3748] overflow-hidden hover:border-blue-500/30 transition-all cursor-pointer"
                onClick={() => setSelectedVideo(video)}
              >
                <div className="aspect-[9/16] bg-gradient-to-br from-gray-800 to-gray-900 relative overflow-hidden">
                  {video.thumbnailPath && (
                    <img
                      src={video.thumbnailPath}
                      alt={video.title}
                      className="w-full h-full object-cover"
                    />
                  )}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                    <div className="w-12 h-12 rounded-full bg-blue-500/80 flex items-center justify-center">
                      <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                    </div>
                  </div>
                  {video.durationSeconds && (
                    <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-0.5 rounded text-xs text-gray-300">
                      {formatDuration(video.durationSeconds)}
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <h3 className="text-sm font-medium text-gray-200 truncate">{video.title}</h3>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-[10px] text-gray-500">
                      {video.createdAt ? new Date(video.createdAt).toLocaleDateString('vi-VN') : ''}
                    </span>
                    {video.feedbackScore && (
                      <span className="text-[10px] text-yellow-400">★ {video.feedbackScore}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedVideo && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedVideo(null)}
        >
          <div
            className="bg-[#1a202c] rounded-2xl border border-[#2d3748] overflow-hidden max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-[#2d3748] flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-200 truncate">{selectedVideo.title}</h3>
              <button
                onClick={() => setSelectedVideo(null)}
                className="p-1 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-gray-200"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="aspect-[9/16] bg-black">
              <video
                src={selectedVideo.videoUrl || selectedVideo.videoPath}
                controls
                className="w-full h-full"
                autoPlay
              />
            </div>
            {selectedVideo.durationSeconds && (
              <div className="p-3 flex items-center gap-4 text-xs text-gray-400">
                <span>Duration: {formatDuration(selectedVideo.durationSeconds)}</span>
                <span>Status: {selectedVideo.status}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
