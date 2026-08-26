import {
  useEffect,
  useState,
} from "react"

import {
  Boxes,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
} from "lucide-react"

import {
  PageHeader,
} from "../../components/ui/PageHeader"

import {
  getCageHistory,
  syncCageHistory,
} from "./cage.api"

import type {
  CageHistoryItem,
} from "./cage.types"


function getToday() {
  const now =
    new Date()

  const year =
    now.getFullYear()

  const month =
    String(
      now.getMonth() + 1,
    ).padStart(
      2,
      "0",
    )

  const day =
    String(
      now.getDate(),
    ).padStart(
      2,
      "0",
    )

  return (
    `${year}-${month}-${day}`
  )
}


function toStartTimestamp(
  value: string,
) {
  if (!value) {
    return 0
  }

  return Math.floor(
    new Date(
      `${value}T00:00:00+07:00`,
    ).getTime()
    /
    1000,
  )
}


function toEndTimestamp(
  value: string,
) {
  if (!value) {
    return 0
  }

  return Math.floor(
    new Date(
      `${value}T23:59:59+07:00`,
    ).getTime()
    /
    1000,
  )
}


function formatTimestamp(
  value?: number | string,
) {
  if (
    value === undefined
    ||
    value === null
    ||
    value === ""
  ) {
    return "-"
  }

  const text =
    String(
      value
    ).trim()

  if (!text) {
    return "-"
  }

  if (
    /^\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}$/
      .test(
        text
      )
  ) {
    return text
  }

  if (
    /^\d{2}\/\d{2}\/\d{4}/
      .test(
        text
      )
  ) {
    return text
  }

  const timestamp =
    Number(
      text
    )

  if (
    !timestamp
    ||
    Number.isNaN(
      timestamp
    )
  ) {
    return text
  }

  const milliseconds =
    timestamp >
    10_000_000_000
      ? timestamp
      : timestamp * 1000

  return (
    new Intl.DateTimeFormat(
      "vi-VN",
      {
        timeZone:
          "Asia/Ho_Chi_Minh",

        day:
          "2-digit",

        month:
          "2-digit",

        year:
          "numeric",

        hour:
          "2-digit",

        minute:
          "2-digit",

        second:
          "2-digit",

        hour12:
          false,
      },
    )
      .format(
        new Date(
          milliseconds
        ),
      )
  )
}


export default function CagePackedHistoryPage() {
  const [
    fromDate,
    setFromDate,
  ] = useState(
    getToday(),
  )

  const [
    toDate,
    setToDate,
  ] = useState(
    getToday(),
  )

  const [
    search,
    setSearch,
  ] = useState(
    "",
  )

  const [
    appliedSearch,
    setAppliedSearch,
  ] = useState(
    "",
  )

  const [
    items,
    setItems,
  ] = useState<
    CageHistoryItem[]
  >(
    [],
  )

  const [
    total,
    setTotal,
  ] = useState(
    0,
  )

  const [
    page,
    setPage,
  ] = useState(
    1,
  )

  const [
    pageSize,
    setPageSize,
  ] = useState(
    100,
  )

  const [
    totalPages,
    setTotalPages,
  ] = useState(
    0,
  )

  const [
    loading,
    setLoading,
  ] = useState(
    false,
  )

  const [
    syncing,
    setSyncing,
  ] = useState(
    false,
  )

  const [
    syncInfo,
    setSyncInfo,
  ] = useState(
    "",
  )

  const [
    error,
    setError,
  ] = useState(
    "",
  )


  async function loadSheet(
    targetPage = 1,
    targetSearch =
      appliedSearch,
    targetPageSize =
      pageSize,
  ) {
    setLoading(
      true
    )

    setError(
      ""
    )

    try {
      const response =
        await getCageHistory(
          targetPage,
          targetPageSize,
          targetSearch,
        )

      if (
        response.success
        === false
      ) {
        throw new Error(
          response.error
          ||
          "Load Sheet error",
        )
      }

      const rows =
        Array.isArray(
          response.data
        )
          ? response.data
          : []

      console.log(
        "CAGE ROWS:",
        rows,
      )

      setItems(
        rows
      )

      setTotal(
        Number(
          response.total
          ||
          0
        )
      )

      setPage(
        Number(
          response.page
          ||
          1
        )
      )

      setPageSize(
        Number(
          response.page_size
          ||
          targetPageSize
        )
      )

      setTotalPages(
        Number(
          response.total_pages
          ||
          0
        )
      )
    } catch (err) {
      console.error(
        "LOAD CAGE ERROR:",
        err,
      )

      setItems(
        []
      )

      setTotal(
        0
      )

      setPage(
        1
      )

      setTotalPages(
        0
      )

      setError(
        err instanceof Error
          ? err.message
          : "Load Sheet error",
      )
    } finally {
      setLoading(
        false
      )
    }
  }


  async function handleLoad() {
    if (
      loading
      ||
      syncing
    ) {
      return
    }

    setSyncInfo(
      ""
    )

    await loadSheet(
      1,
      appliedSearch,
      pageSize,
    )
  }


  async function handleSync() {
    if (
      loading
      ||
      syncing
    ) {
      return
    }

    const begin =
      toStartTimestamp(
        fromDate
      )

    const end =
      toEndTimestamp(
        toDate
      )

    if (
      !begin
      ||
      !end
    ) {
      setError(
        "Vui lòng chọn ngày"
      )

      return
    }

    if (
      begin >
      end
    ) {
      setError(
        "Ngày bắt đầu không hợp lệ"
      )

      return
    }

    setSyncing(
      true
    )

    setError(
      ""
    )

    setSyncInfo(
      ""
    )

    try {
      const response =
        await syncCageHistory(
          begin,
          end,
        )

      if (
        response.success
        === false
      ) {
        throw new Error(
          response.error
          ||
          "Sync error",
        )
      }

      setSyncInfo(
        `SPX: ${response.api_total} | `
        +
        `Inserted: ${response.inserted} | `
        +
        `Updated: ${response.updated} | `
        +
        `Sheet: ${response.total_sheet}`
      )

      setSearch(
        ""
      )

      setAppliedSearch(
        ""
      )

      await loadSheet(
        1,
        "",
        pageSize,
      )
    } catch (err) {
      console.error(
        "SYNC CAGE ERROR:",
        err,
      )

      setError(
        err instanceof Error
          ? err.message
          : "Sync error",
      )
    } finally {
      setSyncing(
        false
      )
    }
  }


  async function handleSearch() {
    if (
      loading
      ||
      syncing
    ) {
      return
    }

    const keyword =
      search
        .trim()

    setAppliedSearch(
      keyword
    )

    await loadSheet(
      1,
      keyword,
      pageSize,
    )
  }


  async function handleClearSearch() {
    if (
      loading
      ||
      syncing
    ) {
      return
    }

    setSearch(
      ""
    )

    setAppliedSearch(
      ""
    )

    await loadSheet(
      1,
      "",
      pageSize,
    )
  }


  async function handlePrevious() {
    if (
      loading
      ||
      syncing
      ||
      page <= 1
    ) {
      return
    }

    await loadSheet(
      page - 1,
      appliedSearch,
      pageSize,
    )
  }


  async function handleNext() {
    if (
      loading
      ||
      syncing
      ||
      totalPages <= 0
      ||
      page >= totalPages
    ) {
      return
    }

    await loadSheet(
      page + 1,
      appliedSearch,
      pageSize,
    )
  }


  async function handlePageSizeChange(
    value: number,
  ) {
    if (
      loading
      ||
      syncing
    ) {
      return
    }

    setPageSize(
      value
    )

    await loadSheet(
      1,
      appliedSearch,
      value,
    )
  }


  useEffect(
    () => {
      void loadSheet(
        1,
        "",
        100,
      )
    },
    [],
  )


  return (
    <>
      <PageHeader
        title="Cage Operations"
        description="Packed Cage History và Google Sheet Sync"
      />

      <section className="panel">
        <div className="panel-title">
          <div>
            <Boxes
              size={17}
            />

            Cage Sync
          </div>

          <span>
            {total} records
          </span>
        </div>

        <div className="panel-body">
          <div
            className="button-row"
            style={{
              alignItems:
                "end",

              flexWrap:
                "wrap",
            }}
          >
            <div>
              <label className="form-label">
                FROM DATE
              </label>

              <input
                className="system-input"
                type="date"
                value={
                  fromDate
                }
                onChange={(event) =>
                  setFromDate(
                    event.target.value
                  )
                }
              />
            </div>

            <div>
              <label className="form-label">
                TO DATE
              </label>

              <input
                className="system-input"
                type="date"
                value={
                  toDate
                }
                onChange={(event) =>
                  setToDate(
                    event.target.value
                  )
                }
              />
            </div>

            <button
              className="primary-button"
              onClick={
                handleSync
              }
              disabled={
                syncing
                ||
                loading
              }
            >
              <RefreshCw
                size={16}
              />

              {
                syncing
                  ? "SYNCING..."
                  : "SYNC SPX → SHEET"
              }
            </button>

            <button
              className="secondary-button"
              onClick={
                handleLoad
              }
              disabled={
                loading
                ||
                syncing
              }
            >
              <RefreshCw
                size={16}
              />

              {
                loading
                  ? "LOADING..."
                  : "LOAD SHEET"
              }
            </button>
          </div>

          {
            syncInfo && (
              <div
                style={{
                  marginTop:
                    "14px",
                }}
              >
                {syncInfo}
              </div>
            )
          }

          {
            error && (
              <div
                style={{
                  marginTop:
                    "14px",

                  color:
                    "#ef4444",
                }}
              >
                {error}
              </div>
            )
          }
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          <div>
            <Search
              size={17}
            />

            Cage History
          </div>

          <span>
            Page {page}
            {" / "}
            {totalPages || 1}
          </span>
        </div>

        <div className="panel-body">
          <div
            className="button-row"
            style={{
              alignItems:
                "end",

              flexWrap:
                "wrap",
            }}
          >
            <div
              style={{
                flex:
                  "1 1 320px",

                maxWidth:
                  "520px",
              }}
            >
              <label className="form-label">
                SEARCH
              </label>

              <input
                className="system-input"
                value={
                  search
                }
                onChange={(event) =>
                  setSearch(
                    event.target.value
                  )
                }
                onKeyDown={(event) => {
                  if (
                    event.key
                    === "Enter"
                  ) {
                    void handleSearch()
                  }
                }}
                placeholder="Shipment ID / Cage / Operator"
              />
            </div>

            <button
              className="secondary-button"
              onClick={
                handleSearch
              }
              disabled={
                loading
                ||
                syncing
              }
            >
              <Search
                size={16}
              />

              SEARCH
            </button>

            <button
              className="secondary-button"
              onClick={
                handleClearSearch
              }
              disabled={
                loading
                ||
                syncing
              }
            >
              CLEAR
            </button>

            <div>
              <label className="form-label">
                ROWS
              </label>

              <select
                className="system-input"
                value={
                  pageSize
                }
                onChange={(event) =>
                  void handlePageSizeChange(
                    Number(
                      event.target.value
                    )
                  )
                }
              >
                <option value={50}>
                  50
                </option>

                <option value={100}>
                  100
                </option>

                <option value={200}>
                  200
                </option>

                <option value={500}>
                  500
                </option>
              </select>
            </div>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>
                  SHIPMENT ID
                </th>

                <th>
                  CAGE
                </th>

                <th>
                  CAGE NAME
                </th>

                <th>
                  SCAN TIME
                </th>

                <th>
                  PACKING START
                </th>

                <th>
                  PACKED TIME
                </th>

                <th>
                  DETACH TIME
                </th>

                <th>
                  OPERATOR
                </th>

                <th>
                  STATION
                </th>

                <th>
                  QTY
                </th>
              </tr>
            </thead>

            <tbody>
              {
                loading && (
                  <tr>
                    <td
                      className="empty-row"
                      colSpan={10}
                    >
                      Loading...
                    </td>
                  </tr>
                )
              }

              {
                !loading
                &&
                items.length === 0
                && (
                  <tr>
                    <td
                      className="empty-row"
                      colSpan={10}
                    >
                      No data
                    </td>
                  </tr>
                )
              }

              {
                !loading
                &&
                items.map(
                  (
                    item,
                    index,
                  ) => (
                    <tr
                      key={
                        item._key
                        ||
                        `${item.mapping_item_number}-${item.mapping_item_scan_time}-${item.cage_id}-${index}`
                      }
                    >
                      <td className="mono">
                        {
                          item.mapping_item_number
                          ||
                          "-"
                        }
                      </td>

                      <td className="mono">
                        {
                          item.cage_id
                          ||
                          "-"
                        }
                      </td>

                      <td>
                        {
                          item.cage_name
                          ||
                          "-"
                        }
                      </td>

                      <td>
                        {
                          formatTimestamp(
                            item.mapping_item_scan_time
                          )
                        }
                      </td>

                      <td>
                        {
                          formatTimestamp(
                            item.cage_packing_start_time
                          )
                        }
                      </td>

                      <td>
                        {
                          formatTimestamp(
                            item.cage_packed_time
                          )
                        }
                      </td>

                      <td>
                        {
                          formatTimestamp(
                            item.detach_time
                          )
                        }
                      </td>

                      <td>
                        {
                          item.operator
                          ||
                          "-"
                        }
                      </td>

                      <td className="mono">
                        {
                          item.station_id
                          ||
                          "-"
                        }
                      </td>

                      <td>
                        {
                          item.parcel_quantity
                          ??
                          "-"
                        }
                      </td>
                    </tr>
                  ),
                )
              }
            </tbody>
          </table>
        </div>

        <div className="panel-body">
          <div
            className="button-row"
            style={{
              justifyContent:
                "space-between",

              alignItems:
                "center",

              flexWrap:
                "wrap",
            }}
          >
            <button
              className="secondary-button"
              onClick={
                handlePrevious
              }
              disabled={
                loading
                ||
                syncing
                ||
                page <= 1
              }
            >
              <ChevronLeft
                size={16}
              />

              PREVIOUS
            </button>

            <div>
              Page{" "}
              <strong>
                {page}
              </strong>

              {" / "}

              <strong>
                {
                  totalPages
                  ||
                  1
                }
              </strong>

              {" | "}

              Total{" "}
              <strong>
                {total}
              </strong>

              {" | "}

              Rows{" "}
              <strong>
                {items.length}
              </strong>
            </div>

            <button
              className="secondary-button"
              onClick={
                handleNext
              }
              disabled={
                loading
                ||
                syncing
                ||
                totalPages <= 0
                ||
                page >= totalPages
              }
            >
              NEXT

              <ChevronRight
                size={16}
              />
            </button>
          </div>
        </div>
      </section>
    </>
  )
}