import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Brain, TrendingUp, Calendar } from 'lucide-react'
import { MemoryCard } from '../components/MemoryCard'
import { SearchBox } from '../components/SearchBox'

type Memory = {
  id: number
  title: string
  tag: string
  relevance: number
  created_at?: string
  category?: string
}

type MemoryStats = {
  total_memories: number
  memories_today: number
  accuracy: number
}

export const MemoryContent: React.FC = () => {
  const [search, setSearch] = useState('')
  const [memories, setMemories] = useState<Memory[]>([])
  const [stats, setStats] = useState<MemoryStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void fetchMemories()
    void fetchStats()
  }, [])

  useEffect(() => {
    if (search) {
      const debounce = setTimeout(() => void fetchMemories(), 300)
      return () => clearTimeout(debounce)
    }
  }, [search])

  async function fetchMemories() {
    try {
      const endpoint = search
        ? `http://127.0.0.1:8000/api/v1/memory/search?query=${encodeURIComponent(search)}`
        : 'http://127.0.0.1:8000/api/v1/memory/recent'
      const res = await fetch(endpoint)
      const data = await res.json()
      const results = data.results || data.memories || []
      const mapped = results.map((item: any) => ({
        id: item.memory_id || item.id,
        title: item.content || item.title || 'Untitled memory',
        tag: item.metadata?.source || item.tag || 'memory',
        relevance: Math.round((item.relevance ?? 1) * 100),
        created_at: item.created_at,
        category: item.metadata?.category || item.category,
      }))
      setMemories(mapped)
    } catch (e) {
      console.error('Failed to fetch memories:', e)
    }
  }

  async function fetchStats() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/memory/stats')
      const data = await res.json()
      setStats(data.memory || data)
      setLoading(false)
    } catch (e) {
      console.error('Failed to fetch stats:', e)
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-[#0A0E27]">
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-[#0F1629]/60 border border-slate-800/40 rounded-lg p-3 backdrop-blur-sm"
            >
              <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                <Brain className="w-3.5 h-3.5" />
                <span className="text-xs font-medium">Total Memories</span>
              </div>
              <p className="text-xl font-semibold text-slate-50">{stats.total_memories}</p>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-[#0F1629]/60 border border-slate-800/40 rounded-lg p-3 backdrop-blur-sm"
            >
              <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                <Calendar className="w-3.5 h-3.5" />
                <span className="text-xs font-medium">Today</span>
              </div>
              <p className="text-xl font-semibold text-slate-50">{stats.memories_today}</p>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-[#0F1629]/60 border border-slate-800/40 rounded-lg p-3 backdrop-blur-sm"
            >
              <div className="flex items-center gap-2 text-slate-400 mb-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                <span className="text-xs font-medium">Accuracy</span>
              </div>
              <p className="text-xl font-semibold text-slate-50">{Math.round(stats.accuracy * 100)}%</p>
            </motion.div>
          </div>
        )}

        {/* Search */}
        <SearchBox 
          value={search} 
          onChange={setSearch} 
          placeholder="Search memories..."
        />
      </div>

      {/* Memory Grid */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          </div>
        ) : memories.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-slate-500">
            No memories found
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((memory, index) => (
              <motion.div
                key={memory.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <MemoryCard 
                  title={memory.title}
                  tag={memory.tag}
                  relevance={memory.relevance}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
