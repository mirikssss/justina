/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
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
