import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, X } from 'lucide-react'

interface KeywordInputProps {
  onSubmit: (keyword: string, options?: KeywordOptions) => void
  loading?: boolean
}

export interface KeywordOptions {
  jobType?: 'all' | 'hourly' | 'fixed'
  priority?: number
  maxPages?: number
}

export function KeywordInput({ onSubmit, loading }: KeywordInputProps) {
  const [keyword, setKeyword] = useState('')
  const [jobType, setJobType] = useState<KeywordOptions['jobType']>('all')
  const [suggestions, setSuggestions] = useState<string[]>([
    'React Developer',
    'Machine Learning Engineer',
    'Full Stack Developer',
    'DevOps Engineer',
    'UI/UX Designer',
  ])

  const handleSubmit = () => {
    if (keyword.trim()) {
      onSubmit(keyword.trim(), { jobType })
      setKeyword('')
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setKeyword(suggestion)
  }

  return (
    <Card className="bg-gray-900/50 border-gray-800">
      <CardHeader>
        <CardTitle className="text-white">Add Keyword to Queue</CardTitle>
        <CardDescription className="text-gray-400">
          Enter a keyword to scrape jobs from Upwork
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-3">
          <Input
            placeholder="Enter keyword (e.g., 'React Developer')"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            className="flex-1 bg-gray-800 border-gray-700 text-white placeholder:text-gray-500"
          />
          <Button
            onClick={handleSubmit}
            disabled={loading || !keyword.trim()}
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add to Queue
          </Button>
        </div>

        {/* Job Type Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Job Type:</span>
          <div className="flex gap-2">
            {(['all', 'hourly', 'fixed'] as const).map((type) => (
              <Badge
                key={type}
                variant={jobType === type ? 'default' : 'outline'}
                className={`cursor-pointer transition-colors ${
                  jobType === type
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                }`}
                onClick={() => setJobType(type)}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </Badge>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        <div>
          <p className="text-sm text-gray-500 mb-2">Suggestions:</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <Badge
                key={suggestion}
                variant="outline"
                className="cursor-pointer bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700 hover:text-white"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
