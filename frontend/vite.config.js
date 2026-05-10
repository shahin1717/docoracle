<<<<<<< HEAD
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
=======
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
>>>>>>> main
