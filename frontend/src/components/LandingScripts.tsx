"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    __bastionTasteBooted?: boolean;
  }
}

export function LandingScripts() {
  useEffect(() => {
    if (window.__bastionTasteBooted) return;
    window.__bastionTasteBooted = true;

    const loadClassic = (src: string) =>
      new Promise<void>((resolve) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = () => resolve();
        script.onerror = () => resolve();
        document.body.appendChild(script);
      });

    const loadModule = (src: string) => {
      const script = document.createElement("script");
      script.type = "module";
      script.src = src;
      document.body.appendChild(script);
    };

    void (async () => {
      await loadClassic("/assets/backgrounds/backgrounds.js");
      loadModule("/assets/system.js");
      loadModule("/assets/motion/motion.js");
      loadModule("/assets/layout/layout.js");
      loadModule("/assets/diagrams/mount.js");
    })();
  }, []);

  return null;
}
