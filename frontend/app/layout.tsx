import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Recall — Institutional Memory for Incident Response",
  description:
    "Self-hosted, open-source Cognee-powered memory for on-call. Every incident makes the next one faster.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <div className="brand">
            <span className="dot" />
            Recall
            <span className="tag">· powered by self-hosted Cognee</span>
          </div>
          <div className="row small muted">
            <a href="https://github.com/topoteretes/cognee" target="_blank" rel="noreferrer">
              Cognee OSS
            </a>
          </div>
        </nav>
        {children}
        <div className="footer">
          Recall — built on open-source Cognee · remember() · recall() · improve() · forget()
        </div>
      </body>
    </html>
  );
}
