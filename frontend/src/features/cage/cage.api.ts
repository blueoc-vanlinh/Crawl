import {
  http,
} from "../../services/http"

import type {
  CageHistoryItem,
  CageHistoryListResponse,
  CageHistorySyncResponse,
} from "./cage.types"


export async function syncCageHistory(
  scanTimeBegin: number,
  scanTimeEnd: number,
): Promise<CageHistorySyncResponse> {
  const response =
    await http.post(
      "/cage/history/sync",
      {
        scan_time_begin:
          scanTimeBegin,

        scan_time_end:
          scanTimeEnd,
      },
    )

  const raw =
    response.data

  return {
    success:
      raw?.success
      ?? true,

    api_total:
      Number(
        raw?.api_total
        ?? 0,
      ),

    inserted:
      Number(
        raw?.inserted
        ?? 0,
      ),

    updated:
      Number(
        raw?.updated
        ?? 0,
      ),

    total_sheet:
      Number(
        raw?.total_sheet
        ?? 0,
      ),

    error:
      raw?.error,
  }
}


export async function getCageHistory(
  page = 1,
  pageSize = 100,
  search = "",
): Promise<CageHistoryListResponse> {
  const response =
    await http.get(
      "/cage/history",
      {
        params: {
          page,

          page_size:
            pageSize,

          search,
        },
      },
    )

  const raw =
    response.data

  console.log(
    "RAW CAGE API:",
    raw,
  )

  let rows:
    CageHistoryItem[] = []

  let meta:
    Record<string, unknown> =
      raw || {}

  if (
    Array.isArray(
      raw?.data,
    )
  ) {
    rows =
      raw.data
  } else if (
    raw?.data
    &&
    typeof raw.data === "object"
    &&
    Array.isArray(
      raw.data.data,
    )
  ) {
    rows =
      raw.data.data

    meta =
      raw.data
  } else if (
    Array.isArray(
      raw?.list,
    )
  ) {
    rows =
      raw.list
  } else if (
    raw?.data
    &&
    typeof raw.data === "object"
    &&
    Array.isArray(
      raw.data.list,
    )
  ) {
    rows =
      raw.data.list

    meta =
      raw.data
  }

  const total =
    Number(
      raw?.total
      ?? meta?.total
      ?? rows.length
      ?? 0,
    )

  const currentPage =
    Number(
      raw?.page
      ?? meta?.page
      ?? page,
    )

  const currentPageSize =
    Number(
      raw?.page_size
      ?? meta?.page_size
      ?? pageSize,
    )

  let totalPages =
    Number(
      raw?.total_pages
      ?? meta?.total_pages
      ?? 0,
    )

  if (
    !totalPages
    &&
    total > 0
    &&
    currentPageSize > 0
  ) {
    totalPages =
      Math.ceil(
        total
        /
        currentPageSize,
      )
  }

  const result:
    CageHistoryListResponse = {
      success:
        raw?.success
        ?? true,

      total,

      page:
        currentPage,

      page_size:
        currentPageSize,

      total_pages:
        totalPages,

      data:
        rows,

      error:
        raw?.error,
    }

  console.log(
    "NORMALIZED CAGE API:",
    result,
  )

  return result
}