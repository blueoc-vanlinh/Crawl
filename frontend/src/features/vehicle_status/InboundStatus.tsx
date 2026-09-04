import {
    useEffect,
    useMemo,
    useState,
} from "react"

import {
    Activity,
    CalendarDays,
    Clock3,
    DownloadCloud,
    Gauge,
    Package,
    RefreshCw,
    Truck,
    Unlock,
} from "lucide-react"

import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts"

import {
    crawlInboundData,
    getVehicleStatus,
} from "./vehicle_status.api"

import type {
    VehicleStatusResponse,
} from "./vehicle_status.types"

import "../../styles/global.css"


function pad(
    value: number,
) {
    return String(value)
        .padStart(2, "0")
}


function getOperationalDate() {
    const now =
        new Date()

    if (
        now.getHours() < 6
    ) {
        now.setDate(
            now.getDate() - 1,
        )
    }

    return [
        now.getFullYear(),
        pad(now.getMonth() + 1),
        pad(now.getDate()),
    ].join("-")
}


function formatDate(
    value: string,
) {
    const parts =
        value.split("-")

    if (
        parts.length !== 3
    ) {
        return value
    }

    return (
        `${parts[2]}/${parts[1]}/${parts[0]}`
    )
}


function formatNumber(
    value:
        number |
        null |
        undefined,
) {
    return Number(
        value ?? 0,
    ).toLocaleString()
}


function Metric({
    label,
    value,
    icon: Icon,
    variant,
}: {
    label: string
    value: number
    icon: typeof Truck
    variant:
    | "blue"
    | "green"
    | "orange"
    | "purple"
}) {
    const iconStyle =
        variant === "purple"
            ? {
                color: "#7c3aed",
                background: "#f5f3ff",
            }
            : undefined

    return (
        <div
            className={
                `status-metric status-metric-${variant}`
            }
        >
            <div
                className="status-metric-icon"
                style={iconStyle}
            >
                <Icon size={20} />
            </div>

            <div>
                <div
                    className="status-metric-label"
                >
                    {label}
                </div>

                <div
                    className="status-metric-value"
                >
                    {
                        formatNumber(
                            value,
                        )
                    }
                </div>
            </div>
        </div>
    )
}


function CustomTooltip({
    active,
    payload,
    label,
}: {
    active?: boolean
    label?: string
    payload?: Array<{
        name?: string
        value?: number
        color?: string
    }>
}) {
    if (
        !active ||
        !payload ||
        payload.length === 0
    ) {
        return null
    }

    return (
        <div
            className="flow-tooltip"
        >
            <div
                className="flow-tooltip-title"
            >
                {label}
            </div>

            {
                payload.map(
                    (
                        item,
                        index,
                    ) => (
                        <div
                            className="flow-tooltip-row"
                            key={
                                `${item.name}-${index}`
                            }
                        >
                            <span>
                                {item.name}
                            </span>

                            <strong>
                                {
                                    formatNumber(
                                        item.value,
                                    )
                                }
                            </strong>
                        </div>
                    ),
                )
            }
        </div>
    )
}


export function InboundStatus() {
    const [
        selectedDate,
        setSelectedDate,
    ] =
        useState(
            getOperationalDate(),
        )

    const [
        data,
        setData,
    ] =
        useState<
            VehicleStatusResponse |
            null
        >(null)

    const [
        loading,
        setLoading,
    ] =
        useState(false)

    const [
        crawling,
        setCrawling,
    ] =
        useState(false)

    const [
        error,
        setError,
    ] =
        useState("")

    const [
        crawlMessage,
        setCrawlMessage,
    ] =
        useState("")


    async function loadData() {
        setLoading(true)
        setError("")

        try {
            const response =
                await getVehicleStatus(
                    selectedDate,
                )

            setData(response)
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Không thể tải dữ liệu",
            )
        } finally {
            setLoading(false)
        }
    }


    async function handleCrawlTrip() {
        if (
            crawling ||
            loading
        ) {
            return
        }

        setCrawling(true)
        setError("")
        setCrawlMessage("")

        try {
            const response =
                await crawlInboundData(
                    selectedDate,
                )

            setCrawlMessage(
                response?.message ||
                "Cào Trip thành công",
            )

            await loadData()
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Không thể cào Trip",
            )
        } finally {
            setCrawling(false)
        }
    }


    useEffect(
        () => {
            void loadData()
        },
        [selectedDate],
    )


    const hourlyData =
        useMemo(
            () => {
                if (
                    !Array.isArray(
                        data?.hourly,
                    )
                ) {
                    return []
                }

                return data!.hourly.map(
                    (row) => ({
                        hour:
                            row.hour,

                        arrived:
                            Number(
                                row.arrived ??
                                0,
                            ),

                        unseal:
                            Number(
                                row.unseal ??
                                0,
                            ),

                        waiting:
                            Number(
                                row.waiting ??
                                0,
                            ),

                        volume:
                            Number(
                                row.volume ??
                                0,
                            ),

                        bulky:
                            Number(
                                row.bulky ??
                                0,
                            ),

                        toCount:
                            Number(
                                row.to_count ??
                                0,
                            ),

                        volumeTripCount:
                            Number(
                                row.volume_trip_count ??
                                0,
                            ),
                    }),
                )
            },
            [data],
        )


    const chartData =
        useMemo(
            () => {
                const rows =
                    hourlyData.map(
                        (row) => ({
                            hour:
                                row.hour,

                            arrived:
                                row.arrived,

                            unseal:
                                row.unseal,

                            waiting:
                                row.waiting,
                        }),
                    )

                rows.push({
                    hour: "06:00",
                    arrived: 0,
                    unseal: 0,
                    waiting:
                        rows[
                            rows.length - 1
                        ]?.waiting ?? 0,
                })

                return rows
            },
            [hourlyData],
        )


    const maxY =
        useMemo(
            () => {
                let max = 0

                for (
                    const row
                    of chartData
                ) {
                    max =
                        Math.max(
                            max,
                            row.arrived,
                            row.unseal,
                            row.waiting,
                        )
                }

                return Math.max(
                    50,
                    Math.ceil(
                        max / 10,
                    ) * 10,
                )
            },
            [chartData],
        )


    const ticks =
        useMemo(
            () => {
                const result:
                    number[] = []

                for (
                    let value = 0;
                    value <= maxY;
                    value += 10
                ) {
                    result.push(
                        value,
                    )
                }

                return result
            },
            [maxY],
        )


    const peakArrival =
        useMemo(
            () => {
                if (
                    chartData.length === 0
                ) {
                    return null
                }

                return chartData.reduce(
                    (
                        best,
                        current,
                    ) =>
                        current.arrived >
                            best.arrived
                            ? current
                            : best,
                    chartData[0],
                )
            },
            [chartData],
        )


    const peakWaiting =
        useMemo(
            () => {
                if (
                    chartData.length === 0
                ) {
                    return null
                }

                return chartData.reduce(
                    (
                        best,
                        current,
                    ) =>
                        current.waiting >
                            best.waiting
                            ? current
                            : best,
                    chartData[0],
                )
            },
            [chartData],
        )


    return (
        <div
            className="inbound-dashboard"
        >
            <section
                className="inbound-topbar"
            >
                <div
                    className="inbound-title-group"
                >
                    <div
                        className="inbound-title-icon"
                    >
                        <Activity
                            size={22}
                        />
                    </div>
                </div>

                <div
                    className="inbound-controls"
                >
                    <div
                        className="inbound-date-picker"
                    >
                        <CalendarDays
                            size={16}
                        />

                        <input
                            type="date"
                            value={
                                selectedDate
                            }
                            disabled={
                                crawling
                            }
                            onChange={
                                (event) => {
                                    setCrawlMessage("")

                                    setSelectedDate(
                                        event.target.value,
                                    )
                                }
                            }
                        />
                    </div>

                    <button
                        type="button"
                        className="inbound-refresh-button"
                        disabled={
                            crawling ||
                            loading
                        }
                        onClick={
                            () => {
                                void handleCrawlTrip()
                            }
                        }
                    >
                        <DownloadCloud
                            size={15}
                            className={
                                crawling
                                    ? "rotating"
                                    : ""
                            }
                        />

                        {
                            crawling
                                ? "Crawling"
                                : "Crawl Trip"
                        }
                    </button>

                    <button
                        type="button"
                        className="inbound-refresh-button"
                        disabled={
                            loading ||
                            crawling
                        }
                        onClick={
                            () => {
                                void loadData()
                            }
                        }
                    >
                        <RefreshCw
                            size={15}
                            className={
                                loading
                                    ? "rotating"
                                    : ""
                            }
                        />

                        {
                            loading
                                ? "Loading"
                                : "Refresh"
                        }
                    </button>
                </div>
            </section>


            {
                error && (
                    <div
                        className="inbound-error"
                    >
                        {error}
                    </div>
                )
            }


            {
                crawlMessage && (
                    <div
                        className="inbound-success"
                    >
                        {crawlMessage}
                    </div>
                )
            }


            <section
                className="inbound-summary-strip"
            >
                <div>
                    <span>
                        Operational Date
                    </span>

                    <strong>
                        {
                            formatDate(
                                selectedDate,
                            )
                        }
                    </strong>
                </div>

                <div>
                    <span>
                        Window
                    </span>

                    <strong>
                        06:00 → 06:00
                    </strong>
                </div>

                <div>
                    <span>
                        Location
                    </span>

                    <strong>
                        Hung Yen SOC
                    </strong>
                </div>

                <div
                    className="inbound-status-online"
                >
                    <span />

                    {
                        crawling
                            ? "Crawling Trip"
                            : "Live data"
                    }
                </div>
            </section>


            <section
                className="inbound-kpi-row"
                style={{
                    gridTemplateColumns:
                        "repeat(4, minmax(0, 1fr))",
                }}
            >
                <Metric
                    label="ARRIVED"
                    value={
                        data?.total
                            ?.arrived ?? 0
                    }
                    icon={Truck}
                    variant="blue"
                />

                <Metric
                    label="UNSEALED"
                    value={
                        data?.total
                            ?.unseal ?? 0
                    }
                    icon={Unlock}
                    variant="green"
                />

                <Metric
                    label="WAITING"
                    value={
                        data?.total
                            ?.waiting ?? 0
                    }
                    icon={Clock3}
                    variant="orange"
                />

                <Metric
                    label="VOLUME"
                    value={
                        data?.volume
                            ?.inbound_order ?? 0
                    }
                    icon={Package}
                    variant="purple"
                />
            </section>


            <section
                className="inbound-main-grid"
            >
                <div
                    className="flow-card"
                >
                    <div
                        className="flow-chart"
                    >
                        <ResponsiveContainer
                            width="100%"
                            height="100%"
                        >
                            <AreaChart
                                data={
                                    chartData
                                }
                                margin={{
                                    top: 20,
                                    right: 18,
                                    left: -10,
                                    bottom: 0,
                                }}
                            >
                                <defs>
                                    <linearGradient
                                        id="arrivalArea"
                                        x1="0"
                                        y1="0"
                                        x2="0"
                                        y2="1"
                                    >
                                        <stop
                                            offset="0%"
                                            stopColor="#3b82f6"
                                            stopOpacity={0.35}
                                        />

                                        <stop
                                            offset="100%"
                                            stopColor="#3b82f6"
                                            stopOpacity={0}
                                        />
                                    </linearGradient>

                                    <linearGradient
                                        id="unsealArea"
                                        x1="0"
                                        y1="0"
                                        x2="0"
                                        y2="1"
                                    >
                                        <stop
                                            offset="0%"
                                            stopColor="#10b981"
                                            stopOpacity={0.18}
                                        />

                                        <stop
                                            offset="100%"
                                            stopColor="#10b981"
                                            stopOpacity={0}
                                        />
                                    </linearGradient>

                                    <linearGradient
                                        id="waitingArea"
                                        x1="0"
                                        y1="0"
                                        x2="0"
                                        y2="1"
                                    >
                                        <stop
                                            offset="0%"
                                            stopColor="#f59e0b"
                                            stopOpacity={0.18}
                                        />

                                        <stop
                                            offset="100%"
                                            stopColor="#f59e0b"
                                            stopOpacity={0}
                                        />
                                    </linearGradient>
                                </defs>

                                <CartesianGrid
                                    stroke="#e5e7eb"
                                    strokeDasharray="3 6"
                                    vertical={false}
                                />

                                <XAxis
                                    dataKey="hour"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{
                                        fill:
                                            "#64748b",
                                        fontSize: 11,
                                    }}
                                    tickMargin={12}
                                />

                                <YAxis
                                    domain={[
                                        0,
                                        maxY,
                                    ]}
                                    ticks={ticks}
                                    axisLine={false}
                                    tickLine={false}
                                    allowDecimals={
                                        false
                                    }
                                    tick={{
                                        fill:
                                            "#94a3b8",
                                        fontSize: 11,
                                    }}
                                />

                                <Tooltip
                                    content={
                                        <CustomTooltip />
                                    }
                                />

                                <Area
                                    type="monotone"
                                    dataKey="arrived"
                                    name="Arrived"
                                    stroke="#2563eb"
                                    strokeWidth={3}
                                    fill="url(#arrivalArea)"
                                    dot={false}
                                    activeDot={{
                                        r: 5,
                                    }}
                                />

                                <Area
                                    type="monotone"
                                    dataKey="unseal"
                                    name="Unseal"
                                    stroke="#059669"
                                    strokeWidth={3}
                                    fill="url(#unsealArea)"
                                    dot={false}
                                    activeDot={{
                                        r: 5,
                                    }}
                                />

                                <Area
                                    type="monotone"
                                    dataKey="waiting"
                                    name="Waiting"
                                    stroke="#d97706"
                                    strokeWidth={3}
                                    fill="url(#waitingArea)"
                                    dot={false}
                                    activeDot={{
                                        r: 5,
                                    }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>


                <aside
                    className="inbound-side-panel"
                >
                    <div
                        className="side-panel-title"
                    >
                        <Gauge size={17} />

                        Live Summary
                    </div>

                    <div
                        className="side-stat"
                    >
                        <span>
                            Peak Arrival
                        </span>

                        <strong>
                            {
                                peakArrival
                                    ? peakArrival.arrived
                                    : 0
                            }
                        </strong>

                        <small>
                            {
                                peakArrival
                                    ? peakArrival.hour
                                    : "-"
                            }
                        </small>
                    </div>

                    <div
                        className="side-stat"
                    >
                        <span>
                            Peak Waiting
                        </span>

                        <strong>
                            {
                                peakWaiting
                                    ? peakWaiting.waiting
                                    : 0
                            }
                        </strong>

                        <small>
                            {
                                peakWaiting
                                    ? peakWaiting.hour
                                    : "-"
                            }
                        </small>
                    </div>

                    <div
                        className="side-stat"
                    >
                        <span>
                            Current Waiting
                        </span>

                        <strong>
                            {
                                data?.total
                                    ?.waiting ?? 0
                            }
                        </strong>

                        <small>
                            vehicle
                        </small>
                    </div>
                </aside>
            </section>


            <section
                className="hourly-table-card"
            >
                <div
                    className="hourly-table-header"
                >
                    <div>
                        <div
                            className="hourly-table-kicker"
                        >
                            HOURLY BREAKDOWN
                        </div>

                        <h2>
                            Vehicle Status by Hour
                        </h2>

                        <p>
                            Arrived, Unseal, Waiting và Volume theo từng mốc giờ
                        </p>
                    </div>

                    <div
                        className="hourly-table-count"
                    >
                        {
                            hourlyData.length
                        } time points
                    </div>
                </div>

                <div
                    className="hourly-table-wrapper"
                >
                    <table
                        className="hourly-table"
                    >
                        <thead>
                            <tr>
                                <th>
                                    TIME
                                </th>

                                <th>
                                    ARRIVED
                                </th>

                                <th>
                                    UNSEAL
                                </th>

                                <th>
                                    WAITING
                                </th>

                                <th>
                                    VOLUME
                                </th>

                                <th>
                                    BULKY
                                </th>

                                <th>
                                    TO COUNT
                                </th>

                                <th>
                                    GAP
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {
                                hourlyData.map(
                                    (row) => {
                                        const gap =
                                            row.arrived -
                                            row.unseal

                                        return (
                                            <tr
                                                key={
                                                    row.hour
                                                }
                                            >
                                                <td>
                                                    <div
                                                        className="hour-cell"
                                                    >
                                                        <Clock3
                                                            size={14}
                                                        />

                                                        <strong>
                                                            {
                                                                row.hour
                                                            }
                                                        </strong>
                                                    </div>
                                                </td>

                                                <td>
                                                    <span
                                                        className="hour-value hour-arrived"
                                                    >
                                                        {
                                                            formatNumber(
                                                                row.arrived,
                                                            )
                                                        }
                                                    </span>
                                                </td>

                                                <td>
                                                    <span
                                                        className="hour-value hour-unseal"
                                                    >
                                                        {
                                                            formatNumber(
                                                                row.unseal,
                                                            )
                                                        }
                                                    </span>
                                                </td>

                                                <td>
                                                    <span
                                                        className={
                                                            row.waiting > 0
                                                                ? "hour-value hour-waiting active"
                                                                : "hour-value hour-waiting"
                                                        }
                                                    >
                                                        {
                                                            formatNumber(
                                                                row.waiting,
                                                            )
                                                        }
                                                    </span>
                                                </td>

                                                <td>
                                                    <strong>
                                                        {
                                                            formatNumber(
                                                                row.volume,
                                                            )
                                                        }
                                                    </strong>
                                                </td>

                                                <td>
                                                    {
                                                        formatNumber(
                                                            row.bulky,
                                                        )
                                                    }
                                                </td>

                                                <td>
                                                    {
                                                        formatNumber(
                                                            row.toCount,
                                                        )
                                                    }
                                                </td>

                                                <td>
                                                    <span
                                                        className={
                                                            gap > 0
                                                                ? "hour-gap positive"
                                                                : gap < 0
                                                                    ? "hour-gap negative"
                                                                    : "hour-gap"
                                                        }
                                                    >
                                                        {
                                                            gap > 0
                                                                ? `+${gap}`
                                                                : gap
                                                        }
                                                    </span>
                                                </td>
                                            </tr>
                                        )
                                    },
                                )
                            }
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}