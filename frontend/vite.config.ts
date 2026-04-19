import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// GitHub Pages project site: set VITE_BASE=/<repo>/ in CI (trailing slash). Local dev: omit for "/".
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE ?? '/',
})
