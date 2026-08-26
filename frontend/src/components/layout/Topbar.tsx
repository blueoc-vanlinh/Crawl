import {
  Bell,
  CircleUserRound,
} from "lucide-react"

import {
  useQuery,
} from "@tanstack/react-query"

import {
  getAuthStatus,
} from "../../features/auth/auth.api"

export function Topbar() {
  const {
    data,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["auth-status"],
    queryFn: getAuthStatus,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    staleTime: Infinity,
  })

  const connected =
    Boolean(
      data?.logged_in &&
      data?.cookie_found &&
      data?.csrf_found,
    )

  return (
    <header className="topbar">
      <div className="environment">
        <span className="environment-label">
          ENV
        </span>

        <strong>
          PRODUCTION
        </strong>
      </div>

      <div className="topbar-right">
        <button
          type="button"
          className={
            connected
              ? "connection-status online"
              : "connection-status offline"
          }
          onClick={() => refetch()}
          disabled={isFetching}
          title="Click để kiểm tra lại SPX"
        >
          <span className="connection-dot" />

          {isLoading || isFetching
            ? "Checking SPX"
            : connected
              ? "SPX Connected"
              : isError
                ? "SPX Disconnected"
                : "SPX Disconnected"}
        </button>

        <button
          className="icon-button"
          type="button"
        >
          <Bell size={18} />
        </button>

        <div className="user-box">
          <CircleUserRound size={21} />

          <div>
            <strong>
              SOC Operator
            </strong>

            <span>
              Operations
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}