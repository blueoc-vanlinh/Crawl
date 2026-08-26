import {
  useMemo,
  useState,
} from "react"

import {
  FileSearch,
  PackageSearch,
  Play,
} from "lucide-react"

import {
  PageHeader,
} from "../../components/ui/PageHeader"

import {
  StatusBadge,
} from "../../components/ui/StatusBadge"

import {
  checkOrder,
  syncOrder,
  syncOrderSheet,
} from "./order.api"

import type {
  SyncResult,
} from "../../types/common"

function now() {
  return new Date()
    .toLocaleTimeString(
      "en-GB",
      {
        hour12: false,
      },
    )
}

export function OrderPage() {
  const [input, setInput] =
    useState("")

  const [running, setRunning] =
    useState(false)

  const [results, setResults] =
    useState<SyncResult[]>(
      [],
    )

  const ids = useMemo(
    () =>
      input
        .split(/[\n,\s]+/)
        .map(
          (item) =>
            item
              .trim()
              .toUpperCase(),
        )
        .filter(Boolean),
    [input],
  )

  async function run(
    mode:
      | "check"
      | "sync",
  ) {
    if (
      running ||
      !ids.length
    ) {
      return
    }

    setRunning(true)

    setResults(
      ids.map((id) => ({
        id,
        status:
          "idle",
        result:
          "Waiting",
        time: "",
        toNumber: "",
        tripNumber: "",
        hyTripTime: "",
      })),
    )

    for (
      const shipmentId
      of ids
    ) {
      setResults(
        (current) =>
          current.map(
            (row) =>
              row.id ===
              shipmentId
                ? {
                    ...row,
                    status:
                      "running",
                    result:
                      "Processing...",
                  }
                : row,
          ),
      )

      try {
        if (
          mode ===
          "check"
        ) {
          const data =
            await checkOrder(
              shipmentId,
            )

          setResults(
            (current) =>
              current.map(
                (row) =>
                  row.id ===
                  shipmentId
                    ? {
                        ...row,

                        status:
                          "success",

                        result:
                          `${
                            data.data
                              ?.new_status ??
                            "-"
                          } | ${
                            data.data
                              ?.new_status_reason ??
                            ""
                          }`,

                        toNumber:
                          data.data
                            ?.to_number ??
                          "",

                        tripNumber:
                          data.data
                            ?.trip_number ??
                          "",

                        hyTripTime:
                          data.data
                            ?.hy_trip_time ??
                          "",

                        time:
                          now(),
                      }
                    : row,
              ),
          )
        } else {
          const data =
            await syncOrder(
              shipmentId,
            )

          setResults(
            (current) =>
              current.map(
                (row) =>
                  row.id ===
                  shipmentId
                    ? {
                        ...row,

                        status:
                          "success",

                        result:
                          `${
                            data.new_status ??
                            "-"
                          } | ${
                            data.new_status_reason ??
                            ""
                          }`,

                        toNumber:
                          data.to_number ??
                          "",

                        tripNumber:
                          data.trip_number ??
                          "",

                        hyTripTime:
                          data.hy_trip_time ??
                          "",

                        time:
                          now(),
                      }
                    : row,
              ),
          )
        }
      } catch (error) {
        setResults(
          (current) =>
            current.map(
              (row) =>
                row.id ===
                shipmentId
                  ? {
                      ...row,

                      status:
                        "error",

                      result:
                        error instanceof
                        Error
                          ? error.message
                          : "Error",

                      time:
                        now(),
                    }
                  : row,
            ),
        )
      }
    }

    setRunning(false)
  }

  async function syncSheet() {
    if (running) {
      return
    }

    setRunning(true)

    try {
      const response =
        await syncOrderSheet(
          20,
        )

      window.alert(
        `Total: ${response.total}\n` +
          `Pushed: ${response.pushed_count}\n` +
          `Failed: ${response.failed_count}`,
      )
    } catch (error) {
      window.alert(
        error instanceof Error
          ? error.message
          : "Sync error",
      )
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Order Operations"
        description="Tracking, TTM Analysis và Google Sheet Sync"
      />

      <section className="panel">
        <div className="panel-title">
          <div>
            <PackageSearch
              size={17}
            />
            Shipment Input
          </div>

          <span>
            {ids.length} orders
          </span>
        </div>

        <div className="panel-body">
          <label className="form-label">
            SHIPMENT ID
          </label>

          <textarea
            className="system-textarea"
            value={input}
            onChange={(e) =>
              setInput(
                e.target.value,
              )
            }
            placeholder={
              "SPXVN068039880298\nSPXVN062640905428"
            }
          />

          <div className="button-row">
            <button
              className="secondary-button"
              onClick={() =>
                run("check")
              }
              disabled={
                running ||
                !ids.length
              }
            >
              <FileSearch
                size={16}
              />
              CHECK TTM
            </button>

            <button
              className="primary-button"
              onClick={() =>
                run("sync")
              }
              disabled={
                running ||
                !ids.length
              }
            >
              <Play size={16} />
              SYNC SELECTED
            </button>

            <button
              className="danger-button"
              onClick={
                syncSheet
              }
              disabled={
                running
              }
            >
              SYNC PUSH ORDER
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          Order Results
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>STATUS</th>
                <th>SHIPMENT ID</th>
                <th>TTM RESULT</th>
                <th>TO</th>
                <th>TRIP</th>
                <th>HY TIME</th>
                <th>CHECK TIME</th>
              </tr>
            </thead>

            <tbody>
              {results.length === 0 && (
                <tr>
                  <td
                    className="empty-row"
                    colSpan={7}
                  >
                    No data
                  </td>
                </tr>
              )}

              {results.map(
                (row) => (
                  <tr key={row.id}>
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

                    <td>
                      {row.result}
                    </td>

                    <td className="mono">
                      {row.toNumber ||
                        "-"}
                    </td>

                    <td className="mono">
                      {row.tripNumber ||
                        "-"}
                    </td>

                    <td>
                      {row.hyTripTime ||
                        "-"}
                    </td>

                    <td>
                      {row.time ||
                        "-"}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}