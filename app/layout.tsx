import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ApplyTrack — Your job search, in focus",
  description: "Track applications, interviews, and follow-ups in one place.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
