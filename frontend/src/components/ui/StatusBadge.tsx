import {
  CheckCircle2,
  Clock3,
  LoaderCircle,
  XCircle,
} from "lucide-react"

import type {
  JobStatus,
} from "../../types/common"

interface Props {
  status: JobStatus
}

export function StatusBadge({
  status,
}: Props) {
  if (status === "success") {
    return (
      <span className="badge success">
        <CheckCircle2 size={14} />
        SUCCESS
      </span>
    )
  }

  if (status === "error") {
    return (
      <span className="badge error">
        <XCircle size={14} />
        ERROR
      </span>
    )
  }

  if (status === "running") {
    return (
      <span className="badge running">
        <LoaderCircle
          size={14}
          className="spin"
        />
        RUNNING
      </span>
    )
  }

  return (
    <span className="badge idle">
      <Clock3 size={14} />
      IDLE
    </span>
  )
}