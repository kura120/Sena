import React from 'react'
import { Copy, RefreshCw } from 'lucide-react'

type MemoryCardProps = {
  title: string
  tag: string
  relevance: number
}

export const MemoryCard: React.FC<MemoryCardProps> = ({ title, tag, relevance }) => {
  return (
    <div className="border border-slate-700 rounded-lg p-4 bg-slate-800/50 hover:bg-slate-800 transition">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-medium text-white">{title}</h3>
        <div className="flex gap-2">
          <button className="p-1.5 hover:bg-slate-700 rounded transition">
            <Copy className="w-4 h-4 text-slate-500" />
          </button>
          <button className="p-1.5 hover:bg-slate-700 rounded transition">
            <RefreshCw className="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="px-2 py-1 text-xs font-semibold bg-purple-900/40 border border-purple-700 text-purple-400 rounded">{tag}</span>
        <span className="text-xs text-slate-400">Relevance: {relevance}%</span>
      </div>
    </div>
  )
}
