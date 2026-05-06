import type { Metadata } from "next";

import { AuthGate } from "@/components/AuthGate";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "StockScope AI",
  description: "Evidence-grounded stock research",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <Navbar />
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
