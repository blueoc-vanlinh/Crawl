export type JobStatus =
  | "idle"
  | "running"
  | "success"
  | "error"

export type LogLevel =
  | "INFO"
  | "RESOLVE"
  | "FETCH"
  | "SHEET"
  | "SUCCESS"
  | "ERROR"

export interface SystemLog {
  id: string
  time: string
  level: LogLevel
  message: string
}

export interface SyncResult {
  id: string
  resolvedId?: string
  status: JobStatus
  result: string
  time: string

  toNumber?: string
  tripNumber?: string
  hyTripTime?: string
}