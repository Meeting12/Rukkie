import { defineConfig } from "vite";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/static/' : '/',
  server: {
    host: "::",
    port: 8080,
    hmr: {
      overlay: false,
    },
  },
  plugins: [],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: 'build',
    assetsDir: 'assets',
    rollupOptions: {
      input: {
        index: path.resolve(__dirname, 'index.html'),
        paymentLinkPage: path.resolve(__dirname, 'src/paymentLinkPage.tsx'),
        paymentLinksAdmin: path.resolve(__dirname, 'src/PaymentLinkAdmin.tsx'),
      },
      output: {
        entryFileNames: ({ name }) => {
          if (name === 'paymentLinkPage') return 'assets/payment-link-page.js';
          if (name === 'paymentLinksAdmin') return 'assets/payment-links-admin.js';
          return 'assets/index.js';
        },
        chunkFileNames: 'assets/chunk-[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === 'index.css') {
            return 'assets/index.css';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
}));

