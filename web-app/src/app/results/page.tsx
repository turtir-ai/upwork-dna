'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ResultsTable } from '@/components'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Search, Download, RefreshCw } from 'lucide-react'
import Link from 'next/link'

interface ScrapedJob {
  id: string | number
  keyword: string
  title: string
  budget?: string
  description?: string
  url: string
  scraped_at?: string
  status?: 'new' | 'contacted' | 'ignored'
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ResultsPage() {
  const [jobs, setJobs] = useState<ScrapedJob[]>([])
  const [filteredJobs, setFilteredJobs] = useState<ScrapedJob[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedKeyword, setSelectedKeyword] = useState<string>('all')

  useEffect(() => {
    fetchResults()
  }, [])

  useEffect(() => {
    let filtered = jobs

    if (searchTerm) {
      filtered = filtered.filter(job =>
        job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        job.description?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (selectedKeyword !== 'all') {
      filtered = filtered.filter(job => job.keyword === selectedKeyword)
    }

    setFilteredJobs(filtered)
  }, [jobs, searchTerm, selectedKeyword])

  const fetchResults = async () => {
    try {
      const response = await fetch(`${API_URL}/results`)
      if (response.ok) {
        const data = await response.json()
        setJobs(data.jobs || data.results || [])
      }
    } catch (error) {
      console.error('Failed to fetch results:', error)
    } finally {
      setLoading(false)
    }
  }

  const keywords = Array.from(new Set(jobs.map(job => job.keyword)))

  const handleContact = async (id: string | number) => {
    try {
      await fetch(`${API_URL}/results/${id}/contact`, { method: 'POST' })
      await fetchResults()
    } catch (error) {
      console.error('Failed to contact:', error)
    }
  }

  const handleIgnore = async (id: string | number) => {
    try {
      await fetch(`${API_URL}/results/${id}/ignore`, { method: 'POST' })
      await fetchResults()
    } catch (error) {
      console.error('Failed to ignore:', error)
    }
  }

  const exportCSV = () => {
    const csv = [
      ['Title', 'Keyword', 'Budget', 'Description', 'URL', 'Date'].join(','),
      ...filteredJobs.map(job =>
        [
          `"${job.title}"`,
          `"${job.keyword}"`,
          `"${job.budget || ''}"`,
          `"${(job.description || '').replace(/"/g, '""')}"`,
          `"${job.url}"`,
          `"${job.scraped_at || ''}"`,
        ].join(',')
      ),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `upwork-jobs-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
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
            <h1 className="text-xl font-bold text-white">Scraped Results</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Filters */}
        <Card className="bg-gray-900/50 border-gray-800 mb-6">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
                <Input
                  placeholder="Search jobs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-gray-800 border-gray-700 text-white"
                />
              </div>

              {/* Keyword Filter */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Keyword:</span>
                <div className="flex flex-wrap gap-2">
                  <Badge
                    variant={selectedKeyword === 'all' ? 'default' : 'outline'}
                    className={`cursor-pointer ${
                      selectedKeyword === 'all'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                    }`}
                    onClick={() => setSelectedKeyword('all')}
                  >
                    All ({jobs.length})
                  </Badge>
                  {keywords.map(keyword => (
                    <Badge
                      key={keyword}
                      variant={selectedKeyword === keyword ? 'default' : 'outline'}
                      className={`cursor-pointer ${
                        selectedKeyword === keyword
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                      }`}
                      onClick={() => setSelectedKeyword(keyword)}
                    >
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchResults}
                  className="border-gray-700 text-gray-300"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={exportCSV}
                  className="border-gray-700 text-gray-300"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export CSV
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Results</CardTitle>
            <CardDescription className="text-gray-400">
              {filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'} found
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResultsTable
              jobs={filteredJobs}
              loading={loading}
              onContact={handleContact}
              onIgnore={handleIgnore}
            />
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
