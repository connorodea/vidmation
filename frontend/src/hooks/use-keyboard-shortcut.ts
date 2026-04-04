"use client";

import { useEffect, useCallback } from "react";

type KeyCombo = {
  key: string;
  meta?: boolean;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
};

export function useKeyboardShortcut(
  combo: KeyCombo,
  callback: () => void,
  enabled: boolean = true
) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Allow meta/ctrl shortcuts even in inputs
      if (isInput && !combo.meta && !combo.ctrl) return;

      const metaMatch = combo.meta ? event.metaKey : !event.metaKey;
      const ctrlMatch = combo.ctrl ? event.ctrlKey : !event.ctrlKey;
      const shiftMatch = combo.shift ? event.shiftKey : true;
      const altMatch = combo.alt ? event.altKey : !event.altKey;
      const keyMatch = event.key.toLowerCase() === combo.key.toLowerCase();

      if (keyMatch && metaMatch && ctrlMatch && shiftMatch && altMatch) {
        event.preventDefault();
        event.stopPropagation();
        callback();
      }
    },
    [combo, callback, enabled]
  );

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown, enabled]);
}
