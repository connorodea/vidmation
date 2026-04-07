"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/components/auth/auth-provider";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";

const PUBLIC_ROUTES = ["/login", "/signup", "/forgot-password", "/landing"];

interface LayoutRouterProps {
  children: React.ReactNode;
}

export function LayoutRouter({ children }: LayoutRouterProps) {
  const pathname = usePathname();
  const isPublicRoute = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  return (
    <AuthProvider>
      {isPublicRoute ? (
        // Public pages render standalone — no sidebar, no guard
        children
      ) : (
        // All other pages get the sidebar shell + auth protection
        <AuthGuard>
          <AppShell>{children}</AppShell>
        </AuthGuard>
      )}
    </AuthProvider>
  );
}
