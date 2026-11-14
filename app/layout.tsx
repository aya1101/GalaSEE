import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TideAware",
  description: "Bản đồ giám sát rừng ngập mặn và phát hiện bất thường.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
