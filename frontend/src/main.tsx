import {
  createRoot,
} from "react-dom/client"

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"

import {
  App,
} from "./app/App"

import "./styles/global.css"

const queryClient =
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        staleTime: Infinity,
      },
    },
  })

createRoot(
  document.getElementById(
    "root",
  )!,
).render(
  <QueryClientProvider
    client={queryClient}
  >
    <App />
  </QueryClientProvider>,
)