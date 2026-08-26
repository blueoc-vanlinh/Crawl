import type {
  ReactNode,
} from "react"

interface Props {
  title: string
  description?: string
  actions?: ReactNode
}

export function PageHeader({
  title,
  description,
  actions,
}: Props) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>

        {description && (
          <p>{description}</p>
        )}
      </div>

      {actions && (
        <div className="page-actions">
          {actions}
        </div>
      )}
    </div>
  )
}