import type { Metadata } from "next";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";
import VersionCheckProvider from "@/components/VersionCheckProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Judi-Expert Site Client",
  description:
    "Site Client d'assistance aux experts judiciaires — Judi-Expert",
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
        <VersionCheckProvider>
          <Header />
          <main style={{ flex: 1, maxWidth: 1200, margin: "0 auto", padding: "24px", width: "100%" }}>
            {children}
          </main>
          <Footer />
          <ChatWidget />
        </VersionCheckProvider>
      </body>
    </html>
  );
}
