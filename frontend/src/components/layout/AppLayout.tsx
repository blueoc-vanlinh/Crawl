import {
  Outlet,
} from "react-router-dom"

import {
  Sidebar,
} from "./Sidebar"

import {
  Topbar,
} from "./Topbar"

export function AppLayout() {
  return (
    <div className="system-shell">
      <Sidebar />

      <div className="system-main">
        <Topbar />

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}