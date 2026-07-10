import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'aespa-static-asset-version',
      enforce: 'post',
      transformIndexHtml(html) {
        return html
          .replace(/src="\/app\.js"/g, 'src="/app.js?v=__AESPA_ASSET_VERSION__"')
          .replace(/href="\/styles\.css"/g, 'href="/styles.css?v=__AESPA_ASSET_VERSION__"')
      },
    },
  ],
  build: { 
    outDir: '../src/aespa/web',
    emptyOutDir: true,
    minify: 'esbuild',
    rolldownOptions: {
      output: {
        keepNames: true,
        codeSplitting: {
          groups: [
            {
              name: 'react-vendor',
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 30,
            },
            {
              name: 'vendor',
              test: /node_modules[\\/]/,
              priority: 20,
            },
            {
              name: 'common',
              minShareCount: 2,
              minSize: 0,
              priority: 10,
            },
          ],
        },
        entryFileNames: 'app.js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const name = assetInfo.names?.[0] || assetInfo.name || ''
          if (name.endsWith('.css')) return 'styles.css'
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
