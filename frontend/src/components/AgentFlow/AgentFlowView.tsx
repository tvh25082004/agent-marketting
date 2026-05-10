'use client'

import type { WorkflowStep, TaskDetail } from '@/types'
import { STEP_LABELS } from '@/types'

interface AgentFlowViewProps {
  steps: WorkflowStep[]
  currentTask: TaskDetail | null
}

export function AgentFlowView({ steps, currentTask }: AgentFlowViewProps) {
  const getStepStatus = (stepName: string): 'pending' | 'running' | 'completed' | 'failed' => {
    if (!currentTask) return 'pending'

    const step = currentTask.steps?.find((s) => s.stepName === stepName)
    if (!step) return 'pending'
    if (step.status === 'completed') return 'completed'
    if (step.status === 'failed') return 'failed'
    if (step.status === 'running') return 'running'
    return 'pending'
  }

  const getStepTokens = (stepName: string): number => {
    return currentTask?.steps?.find((s) => s.stepName === stepName)?.tokensUsed || 0
  }

  return (
    <aside className="w-80 border-l border-[#2d3748] bg-[#1a202c]/30 overflow-y-auto flex-shrink-0 hidden lg:block">
      <div className="p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          Agent Workflow
        </h2>

        <div className="space-y-2">
          {steps.map((step, index) => {
            const status = getStepStatus(step)
            const tokens = getStepTokens(step)
            return (
              <div
                key={step}
                className={`relative p-3 rounded-xl transition-all ${
                  status === 'running'
                    ? 'step-active bg-blue-500/10 border border-blue-500/30'
                    : status === 'completed'
                    ? 'bg-green-500/5 border border-green-500/20'
                    : status === 'failed'
                    ? 'bg-red-500/10 border border-red-500/30'
                    : 'bg-[#1a202c] border border-[#2d3748] opacity-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                    status === 'failed' ? 'bg-red-500/20 text-red-400' :
                    'bg-gray-700 text-gray-500'
                  }`}>
                    {status === 'completed' ? (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    ) : status === 'running' ? (
                      <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                    ) : status === 'failed' ? (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    ) : (
                      <span className="text-xs">{index + 1}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-gray-200 truncate">
                      {STEP_LABELS[step] || step}
                    </div>
                    {tokens > 0 && (
                      <div className="text-[10px] text-gray-500 mt-0.5">
                        {tokens} tokens
                      </div>
                    )}
                  </div>
                </div>

                {index < steps.length - 1 && (
                  <div className={`absolute left-[1.15rem] top-9 w-0.5 h-4 ${
                    getStepStatus(steps[index + 1]) === 'completed' || status === 'completed'
                      ? 'bg-green-500/30'
                      : 'bg-gray-700'
                  }`} />
                )}
              </div>
            )
          })}
        </div>

        {currentTask && (
          <div className="mt-6 p-3 bg-[#1a202c] rounded-xl border border-[#2d3748]">
            <h3 className="text-xs font-semibold text-gray-400 mb-2">Task Stats</h3>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span className={`font-medium ${
                  currentTask.status === 'completed' ? 'text-green-400' :
                  currentTask.status === 'failed' ? 'text-red-400' :
                  'text-blue-400'
                }`}>
                  {currentTask.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Total Tokens</span>
                <span className="text-gray-200 font-mono">{currentTask.tokensUsed || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Total Cost</span>
                <span className="text-gray-200 font-mono">${(currentTask.totalCost || 0).toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Model</span>
                <span className="text-gray-200">{currentTask.modelUsed || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Steps</span>
                <span className="text-gray-200">{currentTask.steps?.length || 0}</span>
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 p-3 bg-blue-500/5 rounded-xl border border-blue-500/10">
          <h3 className="text-xs font-semibold text-blue-300 mb-1">Powered by</h3>
          <div className="flex flex-wrap gap-1.5">
            <span className="px-2 py-0.5 bg-[#2d3748] rounded text-[10px] text-gray-300">LangGraph</span>
            <span className="px-2 py-0.5 bg-[#2d3748] rounded text-[10px] text-gray-300">Langfuse</span>
            <span className="px-2 py-0.5 bg-[#2d3748] rounded text-[10px] text-gray-300">FastAPI</span>
            <span className="px-2 py-0.5 bg-[#2d3748] rounded text-[10px] text-gray-300">Next.js</span>
            <span className="px-2 py-0.5 bg-[#2d3748] rounded text-[10px] text-gray-300">FFmpeg</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
