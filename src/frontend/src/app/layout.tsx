import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "GenAI Tweets Digest - Weekly AI Insights",
  description: "Stay ahead of the curve with our weekly digest of the most impactful Generative AI content from Twitter. Curated insights, breakthrough research, and trending discussions delivered to your inbox.",
  keywords: ["AI", "Artificial Intelligence", "GenAI", "Machine Learning", "Twitter", "Newsletter", "Digest"],
  authors: [{ name: "GenAI Tweets Digest" }],
  openGraph: {
    title: "GenAI Tweets Digest - Weekly AI Insights",
    description: "Stay ahead of the curve with our weekly digest of the most impactful Generative AI content from Twitter.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "GenAI Tweets Digest - Weekly AI Insights",
    description: "Stay ahead of the curve with our weekly digest of the most impactful Generative AI content from Twitter.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
