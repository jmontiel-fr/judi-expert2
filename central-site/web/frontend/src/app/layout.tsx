import type { Metadata } from "next";
import { AuthProvider } from "@/contexts/AuthContext";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatBot from "@/components/ChatBot";
import "./globals.css";

export const metadata: Metadata = {
  title: "Judi-expert",
  description:
    "Site central Judi-expert — Assistance aux experts judiciaires multi-domaines",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body
        style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
      >
        <AuthProvider>
          <Header />
          <main style={{ flex: 1, maxWidth: 1200, margin: "0 auto", padding: "24px", width: "100%" }}>
            {children}
          </main>
          <Footer />
          <ChatBot />
        </AuthProvider>
      </body>
    </html>
  );
}
