import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sudoku — Number Placement Puzzle",
  description: "Play Sudoku online. Choose from Easy, Medium, Hard, and Expert difficulties. Features notes mode, hints, undo, and auto-solve.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
