import {
  useMemo,
  useState,
} from "react"

import {
  Database,
  PackageSearch,
  Play,
  RotateCcw,
  Truck,
} from "lucide-react"

import {
  PageHeader,
} from "../../components/ui/PageHeader"

import {
  StatusBadge,
} from "../../components/ui/StatusBadge"

import {
  syncTrip,
  syncTripOrders,
} from "./trip.api"

import type {
  TripDirection,
} from "./trip.types"


type TripResultStatus =
  | "idle"
  | "running"
  | "success"
  | "error"


type TripResult = {
  id: string
  resolvedId?: string
  status: TripResultStatus
  result: string
  time: string
}


function currentTime() {
  return new Date().toLocaleTimeString(
    "en-GB",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    },
  )
}


export function TripPage() {
  const [
    input,
    setInput,
  ] = useState("")

  const [
    direction,
    setDirection,
  ] =
    useState<TripDirection>(
      "outbound",
    )

  const [
    sequence,
    setSequence,
  ] = useState(1)

  const [
    running,
    setRunning,
  ] = useState(false)

  const [
    runningMode,
    setRunningMode,
  ] = useState<
    "trip" |
    "order" |
    null
  >(null)

  const [
    processed,
    setProcessed,
  ] = useState(0)

  const [
    results,
    setResults,
  ] = useState<TripResult[]>(
    [],
  )

  const ids =
    useMemo(
      () =>
        input
          .split(
            /[\n,\s]+/,
          )
          .map(
            (value) =>
              value.trim(),
          )
          .filter(Boolean),
      [input],
    )

  const progress =
    ids.length > 0
      ? Math.round(
          (
            processed /
            ids.length
          ) * 100,
        )
      : 0


  function prepareResults() {
    const nextResults:
      TripResult[] =
      ids.map(
        (id) => ({
          id,
          status: "idle",
          result: "Waiting",
          time: "",
        }),
      )

    setResults(
      nextResults,
    )
  }


  function setRowRunning(
    id: string,
    message: string,
  ) {
    setResults(
      (current) =>
        current.map(
          (row): TripResult =>
            row.id === id
              ? {
                  ...row,
                  status:
                    "running",
                  result:
                    message,
                }
              : row,
        ),
    )
  }


  function setRowSuccess(
    id: string,
    resolvedId:
      string | number,
    message: string,
  ) {
    setResults(
      (current) =>
        current.map(
          (row): TripResult =>
            row.id === id
              ? {
                  ...row,
                  resolvedId:
                    String(
                      resolvedId,
                    ),
                  status:
                    "success",
                  result:
                    message,
                  time:
                    currentTime(),
                }
              : row,
        ),
    )
  }


  function setRowError(
    id: string,
    message: string,
  ) {
    setResults(
      (current) =>
        current.map(
          (row): TripResult =>
            row.id === id
              ? {
                  ...row,
                  status:
                    "error",
                  result:
                    message,
                  time:
                    currentTime(),
                }
              : row,
        ),
    )
  }


  async function handleSyncTrip() {
    if (
      running ||
      ids.length === 0
    ) {
      return
    }

    setRunning(true)
    setRunningMode("trip")
    setProcessed(0)

    prepareResults()

    try {
      for (
        let index = 0;
        index < ids.length;
        index++
      ) {
        const id =
          ids[index]

        setRowRunning(
          id,
          "Crawling Trip + TO...",
        )

        try {
          const data =
            await syncTrip(
              id,
              direction,
              sequence,
            )

          const toUnique =
            data.loading
              ?.to_unique ??
            0

          const bulky =
            data.loading
              ?.bulky ??
            0

          const scanToRows =
            data.scan_to
              ?.rows ??
            0

          const ordersReady =
            data.orders_ready ??
            0

          const failedTo =
            data.scan_to
              ?.to_scan_failed ??
            0

          let result =
            `${toUnique} TO | ` +
            `${bulky} Bulky | ` +
            `${scanToRows} ScanTO | ` +
            `${ordersReady} Orders ready`

          if (
            failedTo > 0
          ) {
            result +=
              ` | ${failedTo} TO failed`
          }

          setRowSuccess(
            id,
            data.trip_id,
            result,
          )
        } catch (error) {
          const message =
            error instanceof Error
              ? error.message
              : "Unknown error"

          setRowError(
            id,
            message,
          )
        }

        setProcessed(
          index + 1,
        )
      }
    } finally {
      setRunning(false)
      setRunningMode(null)
    }
  }


  async function handleSyncOrders() {
    if (
      running ||
      ids.length === 0
    ) {
      return
    }

    setRunning(true)
    setRunningMode("order")
    setProcessed(0)

    prepareResults()

    try {
      for (
        let index = 0;
        index < ids.length;
        index++
      ) {
        const id =
          ids[index]

        setRowRunning(
          id,
          "Preparing Orders...",
        )

        try {
          const data =
            await syncTripOrders(
              id,
              {
                limit: 300,
                batchSize: 20,

                onProgress:
                  (
                    orderProgress,
                  ) => {
                    const total =
                      orderProgress.total

                    const done =
                      orderProgress.processed

                    const success =
                      orderProgress.success

                    const failed =
                      orderProgress.failed

                    const pushed =
                      orderProgress.pushed

                    setResults(
                      (current) =>
                        current.map(
                          (
                            row,
                          ): TripResult =>
                            row.id === id
                              ? {
                                  ...row,

                                  resolvedId:
                                    String(
                                      orderProgress
                                        .tripId,
                                    ),

                                  status:
                                    "running",

                                  result:
                                    `${done}/${total} Orders | ` +
                                    `${success} OK | ` +
                                    `${failed} Failed | ` +
                                    `${pushed} Pushed`,
                                }
                              : row,
                        ),
                    )
                  },
              },
            )

          const message =
            `${data.processed}/${data.total} Orders | ` +
            `${data.success} OK | ` +
            `${data.failed} Failed | ` +
            `${data.pushed} Pushed`

          setRowSuccess(
            id,
            data.tripId,
            message,
          )
        } catch (error) {
          const message =
            error instanceof Error
              ? error.message
              : "Unknown error"

          setRowError(
            id,
            message,
          )
        }

        setProcessed(
          index + 1,
        )
      }
    } finally {
      setRunning(false)
      setRunningMode(null)
    }
  }


  function reset() {
    if (running) {
      return
    }

    setInput("")
    setResults([])
    setProcessed(0)
    setRunningMode(null)
  }


  return (
    <>
      <PageHeader
        title="LH Trip Operations"
        description="Crawl Trip + TO trước, sau đó crawl Order riêng"
      />

      <div className="operation-layout">
        <section className="panel">
          <div className="panel-title">
            <div>
              <Truck size={17} />
              Trip Input
            </div>

            <span>
              {ids.length} trips
            </span>
          </div>

          <div className="panel-body">
            <label className="form-label">
              TRIP NUMBER / TRIP ID
            </label>

            <textarea
              className="system-textarea"
              value={input}
              onChange={
                (event) =>
                  setInput(
                    event.target.value,
                  )
              }
              placeholder={
                "LT1Q8B4VHJ9F1\nLT1Q8B4VHJ9F2\n294036307"
              }
            />

            <div className="form-grid">
              <div>
                <label className="form-label">
                  DIRECTION
                </label>

                <select
                  className="form-control"
                  value={direction}
                  onChange={
                    (event) =>
                      setDirection(
                        event.target
                          .value as
                          TripDirection,
                      )
                  }
                >
                  <option value="outbound">
                    Outbound
                  </option>

                  <option value="inbound">
                    Inbound
                  </option>
                </select>
              </div>

              <div>
                <label className="form-label">
                  SEQUENCE
                </label>

                <input
                  className="form-control"
                  type="number"
                  min={1}
                  value={sequence}
                  onChange={
                    (event) => {
                      const value =
                        Number(
                          event.target
                            .value,
                        )

                      setSequence(
                        Number.isFinite(
                          value,
                        ) &&
                        value >= 1
                          ? value
                          : 1,
                      )
                    }
                  }
                />
              </div>
            </div>

            <div className="button-row">
              <button
                type="button"
                className="primary-button"
                onClick={
                  handleSyncTrip
                }
                disabled={
                  running ||
                  ids.length === 0
                }
              >
                <Play size={16} />

                {
                  runningMode ===
                  "trip"
                    ? "SYNCING TRIP..."
                    : "SYNC TRIP + TO"
                }
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={
                  handleSyncOrders
                }
                disabled={
                  running ||
                  ids.length === 0
                }
              >
                <PackageSearch
                  size={16}
                />

                {
                  runningMode ===
                  "order"
                    ? "CRAWLING ORDER..."
                    : "CRAWL ORDER"
                }
              </button>

              <button
                type="button"
                className="secondary-button"
                onClick={reset}
                disabled={running}
              >
                <RotateCcw
                  size={16}
                />

                Reset
              </button>
            </div>
          </div>
        </section>

        <section className="panel task-panel">
          <div className="panel-title">
            Task Information
          </div>

          <div className="task-info">
            <div>
              <span>
                Source
              </span>

              <strong>
                SPX Trip API
              </strong>
            </div>

            <div>
              <span>
                Direction
              </span>

              <strong>
                {direction}
              </strong>
            </div>

            <div>
              <span>
                Sequence
              </span>

              <strong>
                {sequence}
              </strong>
            </div>

            <div>
              <span>
                Mode
              </span>

              <strong>
                {
                  runningMode ===
                  "trip"
                    ? "Trip + TO"
                    : runningMode ===
                        "order"
                      ? "Order"
                      : "Ready"
                }
              </strong>
            </div>

            <div>
              <span>
                Destination
              </span>

              <strong>
                Google Sheet
              </strong>
            </div>
          </div>

          <Database
            className="task-watermark"
            size={100}
          />
        </section>
      </div>

      <section className="panel">
        <div className="panel-title">
          Progress

          <strong>
            {processed} /{" "}
            {ids.length}
          </strong>
        </div>

        <div className="progress-container">
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width:
                  `${progress}%`,
              }}
            />
          </div>

          <span>
            {progress}%
          </span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          Sync Results
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>STATUS</th>
                <th>INPUT</th>
                <th>TRIP ID</th>
                <th>RESULT</th>
                <th>TIME</th>
              </tr>
            </thead>

            <tbody>
              {
                results.length ===
                  0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="empty-row"
                    >
                      No data
                    </td>
                  </tr>
                )
              }

              {
                results.map(
                  (row) => (
                    <tr
                      key={row.id}
                    >
                      <td>
                        <StatusBadge
                          status={
                            row.status
                          }
                        />
                      </td>

                      <td className="mono">
                        {row.id}
                      </td>

                      <td className="mono">
                        {
                          row.resolvedId ??
                          "-"
                        }
                      </td>

                      <td>
                        {row.result}
                      </td>

                      <td>
                        {
                          row.time ||
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
      </section>
    </>
  )
}