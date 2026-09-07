import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  build: { target: 'safari16', chunkSizeWarningLimit: 700 },
  server: { headers: { 'Permissions-Policy': 'camera=(self), geolocation=(self), accelerometer=(self), gyroscope=(self), magnetometer=(self)' } },
});
