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
  title: "AIVIDIO — Create Faceless YouTube Videos with AI",
  description:
    "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
  icons: {
    icon: "/aividio-monogram.png",
  },
  openGraph: {
    title: "AIVIDIO — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: [{ url: "/aividio-official.png" }],
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AIVIDIO — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: ["/aividio-official.png"],
  },
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
