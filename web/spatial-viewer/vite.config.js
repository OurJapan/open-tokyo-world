import { defineConfig } from 'vite';
import {fileURLToPath} from 'node:url';
import {localReviewServer} from './scripts/local-review-server.mjs';
export default defineConfig({
  plugins:[localReviewServer(fileURLToPath(new URL('../../',import.meta.url)),process.env.OTW_LOCAL_REVIEW_DIR)],
  cacheDir:fileURLToPath(new URL('../../data/local/vite-cache/',import.meta.url)),
  base: './',
  build: { target: 'safari16', chunkSizeWarningLimit: 700 },
  server: { headers: { 'Permissions-Policy': 'camera=(self), geolocation=(self), accelerometer=(self), gyroscope=(self), magnetometer=(self)' } },
});
