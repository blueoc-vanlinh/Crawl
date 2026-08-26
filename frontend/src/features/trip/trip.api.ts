import type {
  TripDirection,
  TripOrderSyncResponse,
  TripSyncResponse,
} from "./trip.types"


async function readJson<T>(
  response: Response,
): Promise<T> {
  let data: any = null

  try {
    data =
      await response.json()
  } catch {
    throw new Error(
      `HTTP ${response.status}`,
    )
  }

  if (
    !response.ok ||
    data?.success === false
  ) {
    throw new Error(
      data?.error ||
      data?.message ||
      `HTTP ${response.status}`,
    )
  }

  return data as T
}


export async function syncTrip(
  tripId: string,
  direction: TripDirection =
    "outbound",
  sequence = 1,
): Promise<TripSyncResponse> {
  const id =
    String(
      tripId || "",
    ).trim()

  if (!id) {
    throw new Error(
      "Trip ID / Trip Number rỗng",
    )
  }

  const params =
    new URLSearchParams({
      direction:
        String(
          direction,
        ),

      sequence:
        String(
          sequence,
        ),
    })

  const response =
    await fetch(
      `/trip/${encodeURIComponent(
        id,
      )}/sync?${params.toString()}`,
      {
        method:
          "POST",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",
        },
      },
    )

  return readJson<TripSyncResponse>(
    response,
  )
}


export async function syncTripOrdersBatch(
  tripId: string,
  offset = 0,
  limit = 300,
  batchSize = 20,
): Promise<TripOrderSyncResponse> {
  const id =
    String(
      tripId || "",
    ).trim()

  if (!id) {
    throw new Error(
      "Trip ID / Trip Number rỗng",
    )
  }

  const safeOffset =
    Math.max(
      0,
      Number(
        offset,
      ) || 0,
    )

  const safeLimit =
    Math.max(
      1,
      Math.min(
        1000,
        Number(
          limit,
        ) || 300,
      ),
    )

  const safeBatchSize =
    Math.max(
      1,
      Math.min(
        100,
        Number(
          batchSize,
        ) || 20,
      ),
    )

  const params =
    new URLSearchParams({
      offset:
        String(
          safeOffset,
        ),

      limit:
        String(
          safeLimit,
        ),

      batch_size:
        String(
          safeBatchSize,
        ),
    })

  const response =
    await fetch(
      `/trip/${encodeURIComponent(
        id,
      )}/sync-orders?${params.toString()}`,
      {
        method:
          "POST",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",
        },
      },
    )

  return readJson<TripOrderSyncResponse>(
    response,
  )
}


export type TripOrderProgress = {
  tripId:
    string | number

  total:
    number

  processed:
    number

  success:
    number

  failed:
    number

  pushed:
    number

  offset:
    number

  hasMore:
    boolean
}


export async function syncTripOrders(
  tripId: string,
  options?: {
    limit?: number
    batchSize?: number

    onProgress?: (
      progress: TripOrderProgress,
    ) => void
  },
): Promise<{
  tripId:
    string | number

  total:
    number

  processed:
    number

  success:
    number

  failed:
    number

  pushed:
    number

  failedOrders:
    Array<{
      shipment_id:
        string

      error:
        string
    }>

  batches:
    TripOrderSyncResponse[]
}> {
  const limit =
    Math.max(
      1,
      Math.min(
        1000,
        Number(
          options?.limit,
        ) || 300,
      ),
    )

  const batchSize =
    Math.max(
      1,
      Math.min(
        100,
        Number(
          options?.batchSize,
        ) || 20,
      ),
    )

  let offset =
    0

  let total =
    0

  let processed =
    0

  let success =
    0

  let failed =
    0

  let pushed =
    0

  let resolvedTripId:
    string | number =
      tripId

  const failedOrders:
    Array<{
      shipment_id:
        string

      error:
        string
    }> = []

  const batches:
    TripOrderSyncResponse[] =
      []

  while (true) {
    const data =
      await syncTripOrdersBatch(
        tripId,
        offset,
        limit,
        batchSize,
      )

    batches.push(
      data,
    )

    resolvedTripId =
      data.trip_id

    total =
      data.source
        ?.total_unique ??
      total

    const batchCount =
      data.batch
        ?.count ??
      0

    processed +=
      batchCount

    success +=
      data.orders
        ?.success ??
      0

    failed +=
      data.orders
        ?.failed ??
      0

    pushed +=
      data.orders
        ?.pushed ??
      0

    if (
      Array.isArray(
        data.orders
          ?.failed_orders,
      )
    ) {
      failedOrders.push(
        ...data.orders
          .failed_orders,
      )
    }

    const nextOffset =
      data.batch
        ?.next_offset ??
      (
        offset +
        batchCount
      )

    const hasMore =
      Boolean(
        data.batch
          ?.has_more,
      )

    options?.onProgress?.({
      tripId:
        resolvedTripId,

      total,

      processed,

      success,

      failed,

      pushed,

      offset:
        nextOffset,

      hasMore,
    })

    if (!hasMore) {
      break
    }

    if (
      nextOffset <=
      offset
    ) {
      throw new Error(
        "Order pagination không tiến lên",
      )
    }

    offset =
      nextOffset
  }

  return {
    tripId:
      resolvedTripId,

    total,

    processed,

    success,

    failed,

    pushed,

    failedOrders,

    batches,
  }
}