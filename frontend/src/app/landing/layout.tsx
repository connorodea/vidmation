import type { Metadata } from "next";
import { LandingShell } from "./components/landing-shell";

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

export default function LandingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <LandingShell>{children}</LandingShell>;
}
