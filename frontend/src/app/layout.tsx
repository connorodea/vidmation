import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutRouter } from "@/components/layout/layout-router";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AIVidio",
  description: "AI-powered video generation platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <LayoutRouter>{children}</LayoutRouter>
      </body>
    </html>
  );
}
