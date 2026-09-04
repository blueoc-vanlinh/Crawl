export type VehicleStatusHourly = {
    hour: string
    label: string
    from: string
    to: string

    loaded: number
    arrived: number
    unseal: number
    unloaded: number
    waiting: number

    volume: number
    bulky: number
    to_count: number
    volume_trip_count: number
}

export type VehicleStatusTotal = {
    loaded: number
    arrived: number
    unseal: number
    unloaded: number
    waiting: number

    status: {
        loaded: number
        waiting: number
        unseal: number
        unloaded: number
        not_arrived: number
    }
}

export type VolumeSummary = {
    trip_count: number
    inbound_order: number
    bulky: number
    to_count: number
}

export type VehicleStatusResponse = {
    success: boolean

    date: string
    from: string
    to: string
    cutoff: string

    source_rows: number
    latest_rows: number

    hung_yen: number
    inbound: number

    hourly: VehicleStatusHourly[]

    volume: VolumeSummary

    total: VehicleStatusTotal
}