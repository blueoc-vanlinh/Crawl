import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [
    react(),
  ],

  server: {
    host: "0.0.0.0",
    port: 5173,

    allowedHosts: [
      ".trycloudflare.com",
      "localhost",
      "127.0.0.1",
    ],

    proxy: {
      "/auth": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },

      "/trip": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },

      "/trips": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },

      "/order": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },

      "/orders": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
      "/cage": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
})