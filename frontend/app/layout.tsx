import type { Metadata } from "next";

import { FloatingChatButton } from "@/components/FloatingChatButton";
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
        {children}
        <FloatingChatButton />
      </body>
    </html>
  );
}
