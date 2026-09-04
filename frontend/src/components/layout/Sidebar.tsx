import {
  Activity,
  ClipboardList,
  LayoutDashboard,
  Logs,
  PackageSearch,
  Server,
  Truck,
} from "lucide-react"

import {
  NavLink,
} from "react-router-dom"

const menu = [
  {
    path: "/",
    name: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    path: "/inbound",
    name: "Inbound Status",
    icon: Activity,
  },
  {
    path: "/trip",
    name: "LH Trip",
    icon: Truck,
  },
  {
    path: "/orders",
    name: "Orders Delivery",
    icon: PackageSearch,
  },
  {
    path: "/Cage",
    name: "Cage Packed History",
    icon: ClipboardList,
  },
  {
    path: "/jobs",
    name: "Jobs",
    icon: ClipboardList,
  },
  {
    path: "/logs",
    name: "Logs",
    icon: Logs,
  },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <Server size={20} />
        </div>

        <div>
          <strong>SOC</strong>
          <span>
            Operations System
          </span>
        </div>
      </div>

      <div className="sidebar-label">
        OPERATIONS
      </div>

      <nav className="sidebar-nav">
        {menu.map((item) => {
          const Icon = item.icon

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `sidebar-link ${
                  isActive
                    ? "active"
                    : ""
                }`
              }
            >
              <Icon size={18} />

              <span>
                {item.name}
              </span>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-status">
          <Activity size={15} />

          <span>
            Backend :5000
          </span>
        </div>

        <small>
          SOC Operations Platform
        </small>
      </div>
    </aside>
  )
}