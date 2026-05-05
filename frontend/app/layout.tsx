import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";

import { AuthGate } from "@/components/AuthGate";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

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
      <body className={`${dmSans.variable} min-h-screen font-sans antialiased`}>
        <Navbar />
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
