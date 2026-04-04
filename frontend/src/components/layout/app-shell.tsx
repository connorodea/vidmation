"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { CommandPalette } from "@/components/layout/command-palette";
import { useKeyboardShortcut } from "@/hooks/use-keyboard-shortcut";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useKeyboardShortcut(
    { key: "k", meta: true },
    () => setCommandPaletteOpen(true)
  );

  return (
    <>
      <Sidebar />
      <div className="pl-[260px] transition-all duration-200 ease-out">
        <Header onOpenCommandPalette={() => setCommandPaletteOpen(true)} />
        <main className="min-h-[calc(100vh-3.5rem)] p-6">{children}</main>
      </div>
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
      />
    </>
  );
}
