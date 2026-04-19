import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// GitHub Pages: CI sets VITE_BASE=/<repo>/ (trailing slash). Treat blank env as "/" — empty string is not nullish for ??.
function viteBase(): string {
    const raw = process.env.VITE_BASE?.trim()
    if (!raw) return '/'
    return raw.endsWith('/') ? raw : `${raw}/`
}

export default defineConfig({
  plugins: [react()],
  base: viteBase(),
})
