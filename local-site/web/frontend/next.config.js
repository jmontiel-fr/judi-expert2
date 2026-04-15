/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Standalone output pour le déploiement Docker optimisé
  output: "standalone",

  // Proxy des appels API vers le backend FastAPI
  // Utilise NEXT_PUBLIC_API_URL si défini, sinon http://localhost:8000
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
