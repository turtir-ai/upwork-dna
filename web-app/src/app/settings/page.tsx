'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Save, RefreshCw } from 'lucide-react'
import Link from 'next/link'

interface Settings {
  apiUrl: string
  scrapeInterval: number
  maxPages: number
  headless: boolean
  userAgent?: string
  proxy?: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const defaultSettings: Settings = {
  apiUrl: 'http://localhost:8000',
  scrapeInterval: 5000,
  maxPages: 3,
  headless: true,
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    fetchSettings()
    fetchStatus()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/settings`)
      if (response.ok) {
        const data = await response.json()
        setSettings({ ...defaultSettings, ...data })
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
    }
  }

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/status`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Failed to fetch status:', error)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        setSaveMessage('Settings saved successfully!')
        setTimeout(() => setSaveMessage(''), 3000)
      } else {
        setSaveMessage('Failed to save settings')
        setTimeout(() => setSaveMessage(''), 3000)
      }
    } catch (error) {
      console.error('Failed to save settings:', error)
      setSaveMessage('Error saving settings')
      setTimeout(() => setSaveMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async () => {
    setSettings(defaultSettings)
    await handleSave()
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
            <h1 className="text-xl font-bold text-white">Settings</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-4xl">
        {/* System Status */}
        {status && (
          <Card className="bg-gray-900/50 border-gray-800 mb-6">
            <CardHeader>
              <CardTitle className="text-white">System Status</CardTitle>
              <CardDescription className="text-gray-400">Current system information</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">API Version</p>
                  <p className="text-lg font-medium text-white">{status.api_version || '1.0.0'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Uptime</p>
                  <p className="text-lg font-medium text-white">{status.uptime || '0s'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Queue Items</p>
                  <p className="text-lg font-medium text-white">{status.queue_count || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Active Jobs</p>
                  <p className="text-lg font-medium text-white">{status.active_jobs || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Settings Form */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Application Settings</CardTitle>
            <CardDescription className="text-gray-400">Configure your scraping preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* API URL */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">API URL</label>
              <Input
                value={settings.apiUrl}
                onChange={(e) => setSettings({ ...settings, apiUrl: e.target.value })}
                className="bg-gray-800 border-gray-700 text-white"
                placeholder="http://localhost:8000"
              />
            </div>

            {/* Scrape Interval */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">Scrape Interval (ms)</label>
              <Input
                type="number"
                value={settings.scrapeInterval}
                onChange={(e) => setSettings({ ...settings, scrapeInterval: parseInt(e.target.value) })}
                className="bg-gray-800 border-gray-700 text-white"
                min="1000"
                max="60000"
              />
            </div>

            {/* Max Pages */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">Max Pages to Scrape</label>
              <Input
                type="number"
                value={settings.maxPages}
                onChange={(e) => setSettings({ ...settings, maxPages: parseInt(e.target.value) })}
                className="bg-gray-800 border-gray-700 text-white"
                min="1"
                max="10"
              />
            </div>

            {/* Headless Mode */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">Headless Mode</label>
              <Select
                value={settings.headless ? 'true' : 'false'}
                onValueChange={(value) => setSettings({ ...settings, headless: value === 'true' })}
              >
                <SelectTrigger className="bg-gray-800 border-gray-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">Enabled</SelectItem>
                  <SelectItem value="false">Disabled</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* User Agent */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">User Agent (Optional)</label>
              <Textarea
                value={settings.userAgent || ''}
                onChange={(e) => setSettings({ ...settings, userAgent: e.target.value })}
                className="bg-gray-800 border-gray-700 text-white"
                placeholder="Custom user agent string..."
                rows={3}
              />
            </div>

            {/* Proxy */}
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">Proxy URL (Optional)</label>
              <Input
                value={settings.proxy || ''}
                onChange={(e) => setSettings({ ...settings, proxy: e.target.value })}
                className="bg-gray-800 border-gray-700 text-white"
                placeholder="http://proxy.example.com:8080"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-700">
              {saveMessage && (
                <Badge variant={saveMessage.includes('success') ? 'default' : 'destructive'}>
                  {saveMessage}
                </Badge>
              )}
              <div className="flex gap-3 ml-auto">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="border-gray-700 text-gray-300"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Reset to Defaults
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={loading}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                >
                  <Save className="w-4 h-4 mr-2" />
                  Save Settings
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
