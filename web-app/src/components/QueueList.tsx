import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Clock, Play, Trash2, CheckCircle2, XCircle, Loader } from 'lucide-react'

interface QueueItem {
  id: string | number
  keyword: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  job_type?: string
  priority?: number
  created_at?: string
}

interface QueueListProps {
  items: QueueItem[]
  onStart?: (keyword: string) => void
  onRemove?: (id: string | number) => void
}

const statusConfig = {
  pending: {
    icon: <Clock className="w-4 h-4" />,
    label: 'Pending',
    className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  },
  running: {
    icon: <Loader className="w-4 h-4 animate-spin" />,
    label: 'Running',
    className: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  },
  completed: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    label: 'Completed',
    className: 'bg-green-500/20 text-green-400 border-green-500/30',
  },
  failed: {
    icon: <XCircle className="w-4 h-4" />,
    label: 'Failed',
    className: 'bg-red-500/20 text-red-400 border-red-500/30',
  },
}

export function QueueList({ items, onStart, onRemove }: QueueListProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400">No items in queue</p>
        <p className="text-sm text-gray-500 mt-2">Add a keyword to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const config = statusConfig[item.status] || statusConfig.pending

        return (
          <div
            key={item.id}
            className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 hover:bg-gray-800/70 transition-colors"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3 flex-1">
                <div className={config.className}>
                  {config.icon}
                </div>
                <div className="flex-1">
                  <p className="text-white font-medium">{item.keyword}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className={config.className}>
                      {config.label}
                    </Badge>
                    {item.job_type && (
                      <span className="text-xs text-gray-500">{item.job_type}</span>
                    )}
                    {item.priority && (
                      <span className="text-xs text-gray-500">Priority: {item.priority}</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {item.status === 'pending' && onStart && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onStart(item.keyword)}
                    className="text-green-400 border-green-500/30 hover:bg-green-500/10"
                  >
                    <Play className="w-3 h-3 mr-1" />
                    Start
                  </Button>
                )}
                {onRemove && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onRemove(item.id)}
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
            {item.status === 'running' && item.progress !== undefined && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Processing...</span>
                  <span>{item.progress}%</span>
                </div>
                <Progress value={item.progress} className="h-2" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
