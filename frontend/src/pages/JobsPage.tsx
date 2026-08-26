import {
  PageHeader,
} from "../components/ui/PageHeader"

export function JobsPage() {
  return (
    <>
      <PageHeader
        title="Job Management"
        description="Quản lý các tiến trình đồng bộ dữ liệu"
      />

      <section className="panel">
        <div className="panel-title">
          Active Jobs
        </div>

        <div className="empty-state">
          No running jobs
        </div>
      </section>
    </>
  )
}