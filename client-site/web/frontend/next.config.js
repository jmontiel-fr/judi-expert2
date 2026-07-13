/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Standalone output pour le déploiement Docker optimisé
  output: "standalone",

  // Proxy des appels API vers le backend FastAPI (côté serveur)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://judi-web-backend:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
