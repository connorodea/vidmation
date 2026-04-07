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
  title: "AIVidio — Create Faceless YouTube Videos with AI",
  description:
    "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "AIVidio — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: [{ url: "/logo.svg" }],
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AIVidio — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: ["/logo.svg"],
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
