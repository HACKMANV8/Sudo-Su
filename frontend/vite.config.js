import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    root: path.resolve(__dirname, './'),
    build: {
        outDir: 'dist',
    },
    optimizeDeps: {
        include: ['react', 'react-dom', 'firebase/app', 'firebase/auth', 'firebase/database']
    },
    server: {
        port: 5173,
        hot: true
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
})