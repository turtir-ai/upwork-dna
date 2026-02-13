import { Card, CardContent } from '@/components/ui/card'
import { LucideIcon } from 'lucide-react'

interface StatusCardProps {
  title: string
  value: string | number
  icon?: React.ReactNode
  color?: 'green' | 'blue' | 'red' | 'gray' | 'yellow'
}

const colorClasses = {
  green: 'from-green-500/20 to-emerald-500/20 border-green-500/30',
  blue: 'from-blue-500/20 to-indigo-500/20 border-blue-500/30',
  red: 'from-red-500/20 to-rose-500/20 border-red-500/30',
  gray: 'from-gray-500/20 to-zinc-500/20 border-gray-500/30',
  yellow: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30',
}

const textClasses = {
  green: 'text-green-400',
  blue: 'text-blue-400',
  red: 'text-red-400',
  gray: 'text-gray-400',
  yellow: 'text-yellow-400',
}

export function StatusCard({ title, value, icon, color = 'gray' }: StatusCardProps) {
  return (
    <Card className={`bg-gradient-to-br ${colorClasses[color]} border backdrop-blur-sm`}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400 mb-1">{title}</p>
            <p className={`text-2xl font-bold ${textClasses[color]}`}>{value}</p>
          </div>
          {icon && (
            <div className={`${textClasses[color]} opacity-80`}>
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
