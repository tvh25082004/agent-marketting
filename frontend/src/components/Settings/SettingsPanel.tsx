'use client'

import { useState, useEffect } from 'react'
import { getSchedule, updateSchedule, deleteSchedule, getModels, checkHealth } from '@/lib/api'

export function SettingsPanel() {
  const [scheduleEnabled, setScheduleEnabled] = useState(false)
  const [intervalMin, setIntervalMin] = useState(2)
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('gpt-4o')
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null)
  const [healthInfo, setHealthInfo] = useState<{ app: string; version: string; status: string } | null>(null)

  useEffect(() => {
    loadSettings()
    loadModels()
    loadHealth()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await getSchedule()
      setScheduleEnabled(data.enabled)
    } catch { /* ignore */ }
  }

  const loadModels = async () => {
    try {
      const data = await getModels()
      setModels(data.models)
      setSelectedModel(data.default)
    } catch { /* ignore */ }
  }

  const loadHealth = async () => {
    try {
      const data = await checkHealth()
      setHealthInfo(data)
    } catch { /* ignore */ }
  }

  const handleSaveSchedule = async () => {
    setSaving(true)
    try {
      const result = await updateSchedule({
        enabled: scheduleEnabled,
        intervalMinutes: intervalMin,
        maxSongs: 5,
        model: selectedModel,
      })
      setStatus({ ok: true, message: result.message })
    } catch (err: unknown) {
      setStatus({ ok: false, message: err instanceof Error ? err.message : 'Lỗi khi lưu' })
    }
    setSaving(false)
    setTimeout(() => setStatus(null), 3000)
  }

  const handleDeleteSchedule = async () => {
    try {
      await deleteSchedule()
      setScheduleEnabled(false)
      setStatus({ ok: true, message: 'Đã xóa lịch trình' })
    } catch { /* ignore */ }
    setTimeout(() => setStatus(null), 3000)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            Cài đặt hệ thống
          </h2>
        </div>

        <div className="bg-[#1a202c] rounded-2xl border border-[#2d3748] p-5 space-y-5">
          <h3 className="text-sm font-semibold text-gray-300">Lịch trình tự động</h3>

          <label className="flex items-center gap-3 cursor-pointer">
            <div className={`relative w-10 h-5 rounded-full transition-colors ${scheduleEnabled ? 'bg-blue-500' : 'bg-gray-600'}`}>
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${scheduleEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
            <input
              type="checkbox"
              checked={scheduleEnabled}
              onChange={(e) => setScheduleEnabled(e.target.checked)}
              className="hidden"
            />
            <span className="text-sm text-gray-300">Bật crawl tự động</span>
          </label>

          {scheduleEnabled && (
            <div>
              <label className="text-xs text-gray-400 block mb-2">Khoảng thời gian (phút)</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={intervalMin}
                  onChange={(e) => setIntervalMin(Number(e.target.value))}
                  className="flex-1 accent-blue-500"
                />
                <span className="text-sm font-mono text-gray-200 w-10 text-right">{intervalMin}m</span>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">
                Hệ thống sẽ tự động crawl laomusic.net và tạo video mới mỗi {intervalMin} phút
              </p>
            </div>
          )}
        </div>

        <div className="bg-[#1a202c] rounded-2xl border border-[#2d3748] p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Model AI</h3>

          <div>
            <label className="text-xs text-gray-400 block mb-2">Model mặc định</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-[#2d3748] border border-[#3d4758] rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-[#2d3748] rounded-lg p-3">
              <div className="text-gray-500 mb-1">Available Models</div>
              <div className="text-gray-200">{models.length}</div>
            </div>
            <div className="bg-[#2d3748] rounded-lg p-3">
              <div className="text-gray-500 mb-1">Default</div>
              <div className="text-gray-200">{selectedModel}</div>
            </div>
          </div>
        </div>

        <div className="bg-[#1a202c] rounded-2xl border border-[#2d3748] p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Hệ thống</h3>

          {healthInfo && (
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="bg-[#2d3748] rounded-lg p-3">
                <div className="text-gray-500 mb-1">Status</div>
                <div className="text-green-400 font-medium">{healthInfo.status}</div>
              </div>
              <div className="bg-[#2d3748] rounded-lg p-3">
                <div className="text-gray-500 mb-1">Application</div>
                <div className="text-gray-200 truncate">{healthInfo.app}</div>
              </div>
              <div className="bg-[#2d3748] rounded-lg p-3">
                <div className="text-gray-500 mb-1">Version</div>
                <div className="text-gray-200">{healthInfo.version}</div>
              </div>
            </div>
          )}

          <div className="bg-[#2d3748] rounded-lg p-3 text-xs">
            <div className="text-gray-500 mb-2">Crawl Sources</div>
            <div className="text-gray-300 font-mono">https://laomusic.net</div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleSaveSchedule}
            disabled={saving}
            className="flex-1 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl text-sm font-medium transition-colors"
          >
            {saving ? 'Đang lưu...' : 'Lưu cài đặt'}
          </button>
          <button
            onClick={handleDeleteSchedule}
            className="px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl text-sm font-medium transition-colors border border-red-500/20"
          >
            Xóa lịch
          </button>
        </div>

        {status && (
          <div className={`p-3 rounded-xl text-sm ${status.ok ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            {status.message}
          </div>
        )}

        <div className="text-[10px] text-gray-600 text-center pt-4">
          Tinasoft-Agentic-Marketing v1.0.0 · Built with LangGraph + Langfuse
        </div>
      </div>
    </div>
  )
}
