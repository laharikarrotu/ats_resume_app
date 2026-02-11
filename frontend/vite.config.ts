import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      // Forward API calls to FastAPI backend during development
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/upload_resume": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/generate_resume": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/download": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
