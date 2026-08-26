import { http } from "../../services/http"

import type {
  OrderCheckResponse,
  OrderSyncResponse,
  SheetSyncResponse,
} from "./order.types"


export async function checkOrder(
  shipmentId: string,
) {
  const response =
    await http.get<OrderCheckResponse>(
      `/order/${encodeURIComponent(
        shipmentId,
      )}/check`,
    )

  return response.data
}


export async function syncOrder(
  shipmentId: string,
) {
  const response =
    await http.post<OrderSyncResponse>(
      `/order/${encodeURIComponent(
        shipmentId,
      )}/sync`,
    )

  return response.data
}


export async function syncOrderSheet(
  batchSize = 20,
) {
  const response =
    await http.post<SheetSyncResponse>(
      "/orders/sync-sheet",
      null,
      {
        params: {
          batch_size: batchSize,
        },
      },
    )

  return response.data
}


export type TripOrderSyncResponse = {
  success: boolean

  trip_input?: string
  trip_id?: string | number

  source?: {
    scan_to_rows?: number
    bulky_rows?: number
    total_unique?: number
  }

  batch?: {
    offset?: number
    limit?: number
    count?: number
    next_offset?: number
    has_more?: boolean
    max_workers?: number
    elapsed_seconds?: number
  }

  orders?: {
    success?: number
    failed?: number
    pushed?: number

    failed_orders?: Array<{
      shipment_id?: string
      error?: string
      errors?: Array<{
        source?: string
        error?: string
      }>
    }>
  }

  sheet?: {
    inserted?: number
    updated?: number
    unchanged?: number
    skipped?: number
  }

  next_api?: string | null

  error?: string
}


export type TripOrderProgress = {
  offset: number
  total: number
  processed: number
  success: number
  failed: number
  pushed: number
  workers: number
  batch: number
  elapsedSeconds: number
}


function sleep(
  ms: number,
) {
  return new Promise<void>(
    (resolve) => {
      window.setTimeout(
        resolve,
        ms,
      )
    },
  )
}


function randomWorkers() {
  const values = [
    7,
    8,
    9,
  ]

  const index =
    Math.floor(
      Math.random()
      * values.length,
    )

  return values[
    index
  ]
}


export async function syncTripOrdersBatch(
  tripId: string | number,
  options?: {
    offset?: number
    limit?: number
    maxWorkers?: number
  },
) {
  const offset =
    options?.offset
    ?? 0

  const limit =
    options?.limit
    ?? 100

  const maxWorkers =
    options?.maxWorkers
    ?? 8

  const response =
    await http.post<TripOrderSyncResponse>(
      `/trip/${encodeURIComponent(
        String(
          tripId,
        ),
      )}/sync-orders`,
      null,
      {
        params: {
          offset,
          limit,
          max_workers:
            maxWorkers,
        },
      },
    )

  return response.data
}


export async function syncTripOrders(
  tripId: string | number,
  options?: {
    limit?: number

    initialWorkers?: number

    waitMs?: number

    randomWorkerIntervalMs?: number

    onProgress?: (
      progress: TripOrderProgress,
    ) => void
  },
) {
  const limit =
    options?.limit
    ?? 100

  const initialWorkers =
    options?.initialWorkers
    ?? 8

  const waitMs =
    options?.waitMs
    ?? 10000

  const randomWorkerIntervalMs =
    options
      ?.randomWorkerIntervalMs
    ?? 10000

  let offset = 0

  let workers =
    initialWorkers

  let total = 0
  let processed = 0
  let success = 0
  let failed = 0
  let pushed = 0

  let batch = 0

  const startedAt =
    Date.now()

  let lastWorkerChange =
    Date.now()

  const failedOrders:
    Array<{
      shipment_id?: string
      error?: string
      errors?: Array<{
        source?: string
        error?: string
      }>
    }> = []

  while (true) {
    batch += 1

    const now =
      Date.now()

    if (
      batch > 1
      &&
      now
      - lastWorkerChange
      >= randomWorkerIntervalMs
    ) {
      workers =
        randomWorkers()

      lastWorkerChange =
        now
    }

    const result =
      await syncTripOrdersBatch(
        tripId,
        {
          offset,
          limit,
          maxWorkers:
            workers,
        },
      )

    if (!result.success) {
      throw new Error(
        result.error
        || "Không thể sync Order",
      )
    }

    total =
      result.source
        ?.total_unique
      ?? total

    const batchCount =
      result.batch
        ?.count
      ?? 0

    processed +=
      batchCount

    success +=
      result.orders
        ?.success
      ?? 0

    failed +=
      result.orders
        ?.failed
      ?? 0

    pushed +=
      result.orders
        ?.pushed
      ?? 0

    if (
      Array.isArray(
        result.orders
          ?.failed_orders,
      )
    ) {
      failedOrders.push(
        ...result.orders!
          .failed_orders!,
      )
    }

    const elapsedSeconds =
      Math.round(
        (
          Date.now()
          - startedAt
        )
        / 1000,
      )

    options?.onProgress?.({
      offset,
      total,
      processed,
      success,
      failed,
      pushed,
      workers,
      batch,
      elapsedSeconds,
    })

    const hasMore =
      Boolean(
        result.batch
          ?.has_more,
      )

    if (!hasMore) {
      return {
        success:
          true,

        trip_id:
          result.trip_id,

        total,

        processed,

        success_count:
          success,

        failed_count:
          failed,

        pushed_count:
          pushed,

        failed_orders:
          failedOrders,

        batches:
          batch,

        workers,

        elapsed_seconds:
          elapsedSeconds,
      }
    }

    offset =
      result.batch
        ?.next_offset
      ?? (
        offset
        + batchCount
      )

    await sleep(
      waitMs
    )
  }
}