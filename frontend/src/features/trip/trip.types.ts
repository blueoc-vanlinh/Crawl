export type TripDirection =
  | "outbound"
  | "inbound"


export type SheetSyncResult = {
  inserted?:
    number

  updated?:
    number

  unchanged?:
    number

  skipped?:
    number

  [key: string]:
    unknown
}


export type FailedTo = {
  to_number:
    string

  error:
    string
}


export type FailedOrder = {
  shipment_id:
    string

  error:
    string
}


export type TripSyncResponse = {
  success:
    boolean

  trip_input:
    string

  trip_id:
    string | number

  direction:
    TripDirection

  sequence:
    number

  loading: {
    total:
      number

    to_rows:
      number

    to_count:
      number

    to_unique:
      number

    bulky:
      number

    unknown:
      number
  }

  trip: {
    rows:
      number

    sheet:
      SheetSyncResult
  }

  trip_station: {
    rows:
      number

    sheet:
      SheetSyncResult
  }

  to: {
    rows:
      number

    sheet:
      SheetSyncResult
  }

  scan_to: {
    rows:
      number

    to_scan_success:
      number

    to_scan_failed:
      number

    failed_tos:
      FailedTo[]

    sheet:
      SheetSyncResult
  }

  orders_ready:
    number

  next_api:
    string
}


export type TripOrderSource = {
  scan_to_rows:
    number

  bulky_rows:
    number

  total_unique:
    number
}


export type TripOrderBatch = {
  offset:
    number

  limit:
    number

  count:
    number

  next_offset:
    number

  has_more:
    boolean
}


export type TripOrderResult = {
  success:
    number

  failed:
    number

  pushed:
    number

  failed_orders:
    FailedOrder[]
}


export type TripOrderSyncResponse = {
  success:
    boolean

  trip_input:
    string

  trip_id:
    string | number

  source: {
    scan_to_rows:
      number

    bulky_rows:
      number

    total_unique:
      number
  }

  batch: {
    offset:
      number

    limit:
      number

    count:
      number

    next_offset:
      number

    has_more:
      boolean
  }

  orders: {
    success:
      number

    failed:
      number

    pushed:
      number

    failed_orders:
      FailedOrder[]
  }

  sheet:
    SheetSyncResult

  next_api:
    string | null
}