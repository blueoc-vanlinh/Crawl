import type {
  VehicleStatusResponse,
} from "./vehicle_status.types"


export async function getVehicleStatus(
  date?: string,
): Promise<VehicleStatusResponse> {
  const params =
    new URLSearchParams()

  if (date) {
    params.set(
      "date",
      date,
    )
  }

  const query =
    params.toString()

  const response =
    await fetch(
      query
        ? `/api/vehicle-status?${query}`
        : "/api/vehicle-status",
      {
        method: "GET",
        headers: {
          Accept:
            "application/json",
        },
      },
    )

  const data =
    await response.json()

  if (
    !response.ok ||
    data.success === false
  ) {
    throw new Error(
      data.error ||
      data.message ||
      `HTTP ${response.status}`,
    )
  }

  return data
}


export type CrawlTripResponse = {
  success: boolean
  message?: string
  error?: string
  total?: number
  crawled?: number
  inserted?: number
  updated?: number
}


export async function crawlInboundData(
  date: string,
): Promise<CrawlTripResponse> {
  const params =
    new URLSearchParams()

  params.set(
    "date",
    date,
  )

  const response =
    await fetch(
      `/api/trip/daily-crawl?${params.toString()}`,
      {
        method: "POST",
        headers: {
          Accept:
            "application/json",
        },
      },
    )

  const data =
    await response.json()

  if (
    !response.ok ||
    data.success === false
  ) {
    throw new Error(
      data.error ||
      data.message ||
      `HTTP ${response.status}`,
    )
  }

  return data
}