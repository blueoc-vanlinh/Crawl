import type {
  ReactNode,
} from "react"

interface Props {
  label: string
  value: string | number
  icon: ReactNode
}

export function StatCard({
  label,
  value,
  icon,
}: Props) {
  return (
    <div className="stat-card">
      <div>
        <span className="stat-label">
          {label}
        </span>

        <strong className="stat-value">
          {value}
        </strong>
      </div>

      <div className="stat-icon">
        {icon}
      </div>
    </div>
  )
}