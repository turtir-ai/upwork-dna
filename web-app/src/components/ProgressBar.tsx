import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'

interface ProgressBarProps {
  value: number
  max?: number
  label?: string
  showPercentage?: boolean
  color?: 'green' | 'blue' | 'yellow' | 'red'
}

const colorClasses = {
  green: 'bg-green-500',
  blue: 'bg-blue-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
}

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercentage = true,
  color = 'green',
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <Card className="bg-gray-900/50 border-gray-800">
      <CardContent className="p-4">
        {label && (
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">{label}</span>
            {showPercentage && (
              <span className="text-sm text-gray-300">{percentage.toFixed(0)}%</span>
            )}
          </div>
        )}
        <Progress value={percentage} className="h-2" />
        <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
          <span>{value} / {max}</span>
        </div>
      </CardContent>
    </Card>
  )
}
