import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TideAware",
  description: "Evidence-aware coastal intelligence for mangrove protection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
