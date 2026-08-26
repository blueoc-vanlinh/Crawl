import { http } from "../../services/http"

export interface AuthStatus {
  logged_in: boolean
  cookie_found: boolean
  csrf_found: boolean
}

export async function getAuthStatus() {
  const response =
    await http.get<AuthStatus>(
      "/auth/status",
    )

  return response.data
}