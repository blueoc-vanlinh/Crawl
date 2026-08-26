import axios from "axios"

export const http = axios.create({
  baseURL: "",
  timeout: 180000,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const message =
        error.response.data?.error ||
        error.response.data?.message ||
        `HTTP ${error.response.status}`

      return Promise.reject(
        new Error(message),
      )
    }

    if (error.request) {
      return Promise.reject(
        new Error(
          "Không nhận được response từ backend",
        ),
      )
    }

    return Promise.reject(
      new Error(
        error.message ||
          "Unknown API error",
      ),
    )
  },
)