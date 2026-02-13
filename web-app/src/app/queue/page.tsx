'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { QueueList } from '@/components'
import { Button } from '@/components/ui/button'
import { Play, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface QueueItem {
  id: string | number
  keyword: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  job_type?: string
  priority?: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function QueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchQueue()
    const interval = setInterval(fetchQueue, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchQueue = async () => {
    try {
      const response = await fetch(`${API_URL}/queue`)
      if (response.ok) {
        const data = await response.json()
        setQueue(data.items || data.queue || [])
      }
    } catch (error) {
      console.error('Failed to fetch queue:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async (keyword: string) => {
    try {
      const response = await fetch(`${API_URL}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword }),
      })
      if (response.ok) {
        await fetchQueue()
      }
    } catch (error) {
      console.error('Failed to start scraping:', error)
    }
  }

  const handleRemove = async (id: string | number) => {
    try {
      await fetch(`${API_URL}/queue/${id}`, { method: 'DELETE' })
      await fetchQueue()
    } catch (error) {
      console.error('Failed to remove item:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="sm" className="text-gray-300 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Queue Management</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Scraping Queue</CardTitle>
            <CardDescription className="text-gray-400">
              {queue.length} items in queue
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading queue...</p>
              </div>
            ) : (
              <QueueList items={queue} onStart={handleStart} onRemove={handleRemove} />
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
