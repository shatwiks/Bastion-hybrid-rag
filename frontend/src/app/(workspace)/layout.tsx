import type { Metadata } from "next";
import { DM_Mono, Urbanist } from "next/font/google";
import "../globals.css";

const urbanist = Urbanist({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Bastion Workspace: Multi-tenant Hybrid RAG inspector",
  description:
    "Interactive multi-tenant Hybrid RAG workspace with pre-retrieval SQL RBAC, Cross-Encoder refusal gating, and live 6-step telemetry.",
};

export default function WorkspaceRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-type="software"
      data-radius="sharp"
      className={`${urbanist.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body
        className="min-h-screen bg-[var(--ground)] text-[var(--ink)] font-sans antialiased"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
