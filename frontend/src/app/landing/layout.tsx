import type { Metadata } from "next";
import { LandingShell } from "./components/landing-shell";

export const metadata: Metadata = {
  title: "AIVIDIO — Create Faceless YouTube Videos with AI",
  description:
    "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "AIVIDIO — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: [{ url: "/aividio-logo.png" }],
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "AIVIDIO — Create Faceless YouTube Videos with AI",
    description:
      "From topic to published video in minutes. AI writes, narrates, and produces professional videos.",
    images: ["/aividio-logo.png"],
  },
};

export default function LandingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <LandingShell>{children}</LandingShell>;
}
