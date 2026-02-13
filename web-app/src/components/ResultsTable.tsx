import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ExternalLink, Calendar, DollarSign, FileText } from 'lucide-react'

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

interface ResultsTableProps {
  jobs: ScrapedJob[]
  loading?: boolean
  onContact?: (id: string | number) => void
  onIgnore?: (id: string | number) => void
}

const statusConfig = {
  new: { label: 'New', className: 'bg-green-500/20 text-green-400 border-green-500/30' },
  contacted: { label: 'Contacted', className: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  ignored: { label: 'Ignored', className: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
}

export function ResultsTable({ jobs, loading, onContact, onIgnore }: ResultsTableProps) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
        <p className="text-gray-400">Loading results...</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400">No results yet</p>
        <p className="text-sm text-gray-500 mt-2">Start scraping to see results here</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-700 overflow-hidden">
      <Table>
        <TableHeader className="bg-gray-800/50">
          <TableRow className="border-gray-700 hover:bg-gray-800/50">
            <TableHead className="text-gray-300">Title</TableHead>
            <TableHead className="text-gray-300">Keyword</TableHead>
            <TableHead className="text-gray-300">Budget</TableHead>
            <TableHead className="text-gray-300">Status</TableHead>
            <TableHead className="text-gray-300">Date</TableHead>
            <TableHead className="text-gray-300 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => {
            const status = job.status || 'new'
            const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.new

            return (
              <TableRow key={job.id} className="border-gray-700 hover:bg-gray-800/30">
                <TableCell className="font-medium text-white">
                  <div className="max-w-md">
                    <p className="truncate">{job.title}</p>
                    {job.description && (
                      <p className="text-xs text-gray-500 truncate mt-1">{job.description}</p>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="bg-gray-800 text-gray-300 border-gray-600">
                    {job.keyword}
                  </Badge>
                </TableCell>
                <TableCell>
                  {job.budget ? (
                    <div className="flex items-center gap-1 text-green-400">
                      <DollarSign className="w-3 h-3" />
                      <span>{job.budget}</span>
                    </div>
                  ) : (
                    <span className="text-gray-500">-</span>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={config.className}>
                    {config.label}
                  </Badge>
                </TableCell>
                <TableCell>
                  {job.scraped_at ? (
                    <div className="flex items-center gap-1 text-gray-400 text-sm">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(job.scraped_at).toLocaleDateString()}</span>
                    </div>
                  ) : (
                    <span className="text-gray-500">-</span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => window.open(job.url, '_blank')}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                    {onContact && status === 'new' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onContact(job.id)}
                        className="text-green-400 hover:text-green-300"
                      >
                        Contact
                      </Button>
                    )}
                    {onIgnore && status !== 'ignored' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onIgnore(job.id)}
                        className="text-gray-400 hover:text-gray-300"
                      >
                        Ignore
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
