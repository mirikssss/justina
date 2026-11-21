/** @type {import('next').NextConfig} */
const API_PROXY_URL = process.env.API_PROXY_URL ?? "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      // Приём снимков от локального сборщика (documents sync): единственный внутренний маршрут, открытый наружу.
      // Caddy режет /api/internal/*, а здесь защита — подпись HMAC (X-Signature, окно 5 минут) и идемпотентность по snapshot_id.
      { source: "/agent/internal/ingest/snapshots", destination: `${API_PROXY_URL}/internal/ingest/snapshots` },
      { source: "/api/:path*", destination: `${API_PROXY_URL}/:path*` },
    ];
  },
  async headers() {
    // Строгие заголовки: модалку подтверждения нельзя встроить в чужой iframe
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "Referrer-Policy", value: "same-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
