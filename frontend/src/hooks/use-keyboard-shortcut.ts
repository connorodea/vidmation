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
  const { key, meta, ctrl, shift, alt } = combo;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Allow meta/ctrl shortcuts even in inputs
      if (isInput && !meta && !ctrl) return;

      const metaMatch = meta ? event.metaKey : !event.metaKey;
      const ctrlMatch = ctrl ? event.ctrlKey : !event.ctrlKey;
      const shiftMatch = shift ? event.shiftKey : true;
      const altMatch = alt ? event.altKey : !event.altKey;
      const keyMatch = event.key.toLowerCase() === key.toLowerCase();

      if (keyMatch && metaMatch && ctrlMatch && shiftMatch && altMatch) {
        event.preventDefault();
        event.stopPropagation();
        callback();
      }
    },
    [key, meta, ctrl, shift, alt, callback, enabled]
  );

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown, enabled]);
}
