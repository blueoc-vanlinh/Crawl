export interface OrderCheckResponse {
  success: boolean

  data?: {
    shipment_id?: string

    new_status?: string
    new_status_time?: string
    new_status_reason?: string

    next_station?: string

    latest_status?: string
    latest_status_time?: string

    to_number?: string
    trip_number?: string
    hy_trip_time?: string
  }

  error?: string
}

export interface OrderSyncResponse {
  success: boolean

  shipment_id: string

  new_status?: string
  new_status_time?: string
  new_status_reason?: string

  next_station?: string

  to_number?: string
  trip_number?: string
  hy_trip_time?: string

  sheet?: unknown
  error?: string
}

export interface SheetSyncResponse {
  success: boolean
  total: number
  success_count: number
  failed_count: number
  pushed_count: number
  failed_orders?: Array<{
    shipment_id: string
    error: string
  }>
}