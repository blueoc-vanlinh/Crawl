export interface CageHistoryItem {
  _key?: string

  cage_id?: string
  cage_name?: string

  mapping_item_number?: string
  mapping_item_type?: number | string

  mapping_item_scan_time?: number | string
  cage_packing_start_time?: number | string
  cage_packed_time?: number | string
  detach_time?: number | string
  ctime?: number | string
  mtime?: number | string

  parcel_quantity?: number | string
  station_id?: number | string
  cage_type?: number | string

  operator?: string

  high_value?: number | string
  dg_type?: number | string

  cage_exception_type_list?: unknown
  cage_exception_type_list_string?: string

  [key: string]: unknown
}


export interface CageHistorySyncResponse {
  success: boolean

  api_total: number
  inserted: number
  updated: number
  total_sheet: number

  error?: string
}


export interface CageHistoryListResponse {
  success: boolean

  total: number
  page: number
  page_size: number
  total_pages: number

  data: CageHistoryItem[]

  error?: string
}