import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Architecture Studio",
  description: "See your exterior renovation before you build it.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
