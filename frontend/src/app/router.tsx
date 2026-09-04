import {
  createBrowserRouter,
} from "react-router-dom"

import {
  AppLayout,
} from "../components/layout/AppLayout"

import {
  DashboardPage,
} from "../pages/DashboardPage"

import {
  TripPage,
} from "../features/trip/TripPage"

import {
  OrderPage,
} from "../features/order/OrderPage"

import CagePackedHistoryPage
  from "../features/cage/CagePackedHistoryPage"

import {
  InboundStatus
} from "../features/vehicle_status/InboundStatus"

import {
  JobsPage,
} from "../pages/JobsPage"

import {
  LogsPage,
} from "../pages/LogsPage"

export const router =
  createBrowserRouter([
    {
      path: "/",
      element:
        <AppLayout />,
      children: [
        {
          index: true,
          element:
            <DashboardPage />,
        },
        {
          path: "inbound",
          element:
            <InboundStatus />,
        },
        {
          path: "Trip",
          element:
            <TripPage />,
        },
        {
          path: "orders",
          element:
            <OrderPage />,
        },
        {
          path: "Cage",
          element:
            <CagePackedHistoryPage />,
        },
        {
          path: "Jobs",
          element:
            <JobsPage />,
        },
        {
          path: "Logs",
          element:
            <LogsPage />,
        },
      ],
    },
  ])