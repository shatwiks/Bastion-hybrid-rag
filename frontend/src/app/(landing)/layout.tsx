import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Bastion: Multi-tenant Hybrid RAG engine for engineering teams",
  description:
    "Pre-retrieval SQL RBAC inside PostgreSQL, pgvector and BM25 fusion, Cross-Encoder refusal gating below 0.65, and live pipeline telemetry.",
  openGraph: {
    type: "website",
    title: "Bastion: Multi-tenant Hybrid RAG engine for engineering teams",
    description:
      "Pre-retrieval SQL RBAC inside PostgreSQL, pgvector and BM25 fusion, Cross-Encoder refusal gating below 0.65, and live pipeline telemetry.",
    images: ["/share.png"],
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function LandingRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-type="software"
      data-radius="sharp"
      data-ground="sand"
      data-buttons="tonal"
      data-motion=""
      suppressHydrationWarning
    >
      <head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
        <meta name="theme-color" content="#dfdedb" />
        <meta name="site-kind" content="software" />
        <meta name="page-type" content="software" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400..700&family=DM+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <link rel="stylesheet" href="/assets/system.css" />
        <link rel="stylesheet" href="/assets/ui/cards.css" />
        <link rel="stylesheet" href="/assets/motion/motion.css" />
        <link rel="stylesheet" href="/assets/backgrounds/backgrounds.css" />
        <link rel="stylesheet" href="/assets/layout/layout.css" />
        <link rel="stylesheet" href="/assets/icons/icon.css" />
        <link rel="stylesheet" href="/assets/ui/base.css" />
        <link rel="stylesheet" href="/assets/ui/window/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/pipeline-board/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/chat/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/terminal-run/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/search/fragment.css" />
        <link rel="stylesheet" href="/assets/ui/stat/fragment.css" />
        <link rel="stylesheet" href="/assets/diagrams/diagram.css" />
        <link
          rel="stylesheet"
          href="/assets/moments/pinned-chapters/moment.css"
        />
        <link rel="stylesheet" href="/assets/bastion-landing.css" />
        <script src="/assets/bastion-enter.js" />
        <link rel="modulepreload" href="/assets/moments/moments.js" />
        <link rel="modulepreload" href="/assets/moments/lib.js" />
        <link
          rel="modulepreload"
          href="/assets/moments/pinned-chapters/moment.js"
        />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
