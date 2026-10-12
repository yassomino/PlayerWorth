import type { Metadata } from "next";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
export const metadata: Metadata = {
  title: {
    default: "PlayerWorth — Football Market Value Analytics",
    template: "%s | PlayerWorth",
  },
  description:
    "Explore model-estimated Premier League player values using historical performance data.",
  openGraph: {
    type: "website",
    siteName: "PlayerWorth",
    title: "PlayerWorth — The game. Another value.",
    description:
      "Explore Premier League model estimates, historical performance and the evidence behind PlayerWorth V1.",
  },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Navbar />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
