/** @type {import('next').NextConfig} */
const API_PROXY_URL = process.env.API_PROXY_URL ?? "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_PROXY_URL}/:path*` }];
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
