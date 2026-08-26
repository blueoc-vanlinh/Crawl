import {
  Activity,
  Boxes,
  ClipboardCheck,
  Truck,
} from "lucide-react"

import {
  PageHeader,
} from "../components/ui/PageHeader"

import {
  StatCard,
} from "../components/ui/StatCard"

export function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Operations Dashboard"
        description="Tổng quan vận hành SOC Data Sync"
      />

      <div className="stats-grid">
        <StatCard
          label="TRIP SYNCED"
          value="128"
          icon={<Truck size={23} />}
        />

        <StatCard
          label="ORDER SYNCED"
          value="1,420"
          icon={<Boxes size={23} />}
        />

        <StatCard
          label="RUNNING JOBS"
          value="0"
          icon={
            <Activity size={23} />
          }
        />

        <StatCard
          label="SUCCESS RATE"
          value="99.2%"
          icon={
            <ClipboardCheck
              size={23}
            />
          }
        />
      </div>

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-title">
            System Overview
          </div>

          <div className="system-grid">
            <div>
              <span>Frontend</span>
              <strong>
                React TypeScript
              </strong>
            </div>

            <div>
              <span>Backend</span>
              <strong>
                Flask API
              </strong>
            </div>

            <div>
              <span>SPX</span>
              <strong>
                Authentication
              </strong>
            </div>

            <div>
              <span>Storage</span>
              <strong>
                Google Sheets
              </strong>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-title">
            System Architecture
          </div>

          <div className="architecture">
            <div>Operator</div>
            <span>→</span>
            <div>React</div>
            <span>→</span>
            <div>Flask</div>
            <span>→</span>
            <div>SPX</div>
            <span>→</span>
            <div>Sheet</div>
          </div>
        </section>
      </div>
    </>
  )
}