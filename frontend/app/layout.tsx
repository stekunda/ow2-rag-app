import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OW2 Hero Intelligence",
  description: "RAG-powered Overwatch 2 hero intelligence chatbot"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
