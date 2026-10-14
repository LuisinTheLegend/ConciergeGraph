import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Grafo Dashboard — Concierge MCP",
  description:
    "Painel de diagnóstico e visualização 3D do Grafo de Memória Concierge. Interface de comando para agentes LLM.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="noise-overlay">{children}</body>
    </html>
  );
}
