'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

interface QueueItem {
  id: number
  keyword: string
  status: string
  job_type: string
  priority: number
  created_at: string
}

interface Job {
  id: number
  keyword: string
  title: string
  budget: string
  description: string
  url: string
  scraped_at: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [keyword, setKeyword] = useState('')
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<any>(null)

  // Fetch queue on mount
  useEffect(() => {
    fetchQueue()
    fetchStatus()
    // Poll every 5 seconds
    const interval = setInterval(() => {
      fetchQueue()
      fetchStatus()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchQueue = async () => {
    try {
      const res = await fetch(`${API_URL}/queue`)
      if (res.ok) {
        const data = await res.json()
        setQueue(data.items || [])
      }
    } catch (err) {
      console.error('Failed to fetch queue:', err)
    }
  }

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/status`)
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }

  const addToQueue = async () => {
    if (!keyword.trim()) return

    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/queue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: keyword.trim(),
          job_type: 'all',
          priority: 1
        })
      })

      if (res.ok) {
        setKeyword('')
        await fetchQueue()
      } else {
        alert('Failed to add keyword')
      }
    } catch (err) {
      alert('Error: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const startScraping = async (queueKeyword: string) => {
    try {
      const res = await fetch(`${API_URL}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: queueKeyword,
          job_type: 'all',
          max_pages: 3
        })
      })

      if (res.ok) {
        const data = await res.json()
        alert(`Scraping started! Job ID: ${data.job_id}`)
        await fetchQueue()
      } else {
        alert('Failed to start scraping')
      }
    } catch (err) {
      alert('Error: ' + (err as Error).message)
    }
  }

  const removeFromQueue = async (id: number) => {
    try {
      await fetch(`${API_URL}/queue/${id}`, { method: 'DELETE' })
      await fetchQueue()
    } catch (err) {
      alert('Failed to remove')
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      pending: 'secondary',
      running: 'default',
      completed: 'destructive',
      failed: 'destructive'
    }
    return <Badge variant={variants[status] as any}>{status}</Badge>
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50">
            Upwork DNA
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400">
            Otomatik Upwork Veri Kazıma Sistemi
          </p>
          {status && (
            <div className="flex justify-center gap-4 text-sm">
              <span className="text-zinc-500">Backend: <span className="text-green-500">✓ Connected</span></span>
              <span className="text-zinc-500">Queue: {status.queue_count || 0} items</span>
              <span className="text-zinc-500">Jobs: {status.jobs_count || 0}</span>
              <span className="text-zinc-500">Talent: {status.talent_count || 0}</span>
            </div>
          )}
        </div>

        {/* Add Keyword Card */}
        <Card>
          <CardHeader>
            <CardTitle>Yeni Anahtar Kelime Ekle</CardTitle>
            <CardDescription>
              Upwork'ta aranacak kelimeyi girin ve queue'ya ekleyin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Input
                placeholder="Örn: AI agent, machine learning, python developer"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addToQueue()}
                className="flex-1"
              />
              <Button onClick={addToQueue} disabled={loading}>
                {loading ? 'Ekleniyor...' : 'Queue\'ya Ekle'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="queue" className="space-y-4">
          <TabsList>
            <TabsTrigger value="queue">Queue ({queue.length})</TabsTrigger>
            <TabsTrigger value="results">Sonuçlar</TabsTrigger>
            <TabsTrigger value="status">Sistem Durumu</TabsTrigger>
          </TabsList>

          <TabsContent value="queue" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Scraping Queue</CardTitle>
                <CardDescription>
                  Bekleyen ve çalışan işleri görüntüleyin
                </CardDescription>
              </CardHeader>
              <CardContent>
                {queue.length === 0 ? (
                  <p className="text-center text-zinc-500 py-8">Queue boş</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Anahtar Kelime</TableHead>
                        <TableHead>Durum</TableHead>
                        <TableHead>Tür</TableHead>
                        <TableHead>Öncelik</TableHead>
                        <TableHead>İşlemler</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {queue.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium">{item.keyword}</TableCell>
                          <TableCell>{getStatusBadge(item.status)}</TableCell>
                          <TableCell>{item.job_type}</TableCell>
                          <TableCell>{item.priority}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              {item.status === 'pending' && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => startScraping(item.keyword)}
                                >
                                  Başlat
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => removeFromQueue(item.id)}
                              >
                                Sil
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="results">
            <Card>
              <CardHeader>
                <CardTitle>Scraped Results</CardTitle>
                <CardDescription>
                  Kazınan verileri görüntüleyin
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-center text-zinc-500 py-8">
                  Sonuçlar yükleniyor... API'den /results endpoint ile veri çekilecek
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="status">
            <Card>
              <CardHeader>
                <CardTitle>Sistem Durumu</CardTitle>
              </CardHeader>
              <CardContent>
                {status ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-zinc-500">API Version</p>
                        <p className="text-lg font-medium">{status.api_version || '1.0.0'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-zinc-500">Uptime</p>
                        <p className="text-lg font-medium">{status.uptime || '0s'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-zinc-500">Queue Items</p>
                        <p className="text-lg font-medium">{status.queue_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-sm text-zinc-500">Active Jobs</p>
                        <p className="text-lg font-medium">{status.active_jobs || 0}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-zinc-500">Yükleniyor...</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  )
}
