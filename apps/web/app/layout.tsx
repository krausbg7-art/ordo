import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ordo — дела в порядке",
  description: "ИИ-секретарь руководителя",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,400&family=Manrope:wght@400;500;600;700&display=swap"
        />
      </head>
      <body className="bg-cream text-ink antialiased">{children}</body>
    </html>
  );
}
