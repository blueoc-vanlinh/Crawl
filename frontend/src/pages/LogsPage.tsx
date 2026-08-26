import {
  PageHeader,
} from "../components/ui/PageHeader"

export function LogsPage() {
  return (
    <>
      <PageHeader
        title="System Logs"
        description="Theo dõi hoạt động và lỗi hệ thống"
      />

      <section className="terminal">
        <div>
          <span>
            14:45:01
          </span>

          <strong className="log-info">
            INFO
          </strong>

          SOC Operations System ready
        </div>

        <div>
          <span>
            14:45:02
          </span>

          <strong className="log-success">
            SUCCESS
          </strong>

          Flask backend connected
        </div>
      </section>
    </>
  )
}