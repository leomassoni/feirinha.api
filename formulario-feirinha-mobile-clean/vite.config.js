import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path' // Import necessário para o path.resolve

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()], // Apenas o plugin do React. O Vite detecta o PostCSS automaticamente pelo postcss.config.js.
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})