'use client';

import Hero from '@/components/Hero';
import Features from '@/components/Features';
import Footer from '@/components/Footer';

export default function Home() {
  // No custom handler needed - EmailSignup component will handle API calls directly
  return (
    <main className="min-h-screen">
      <Hero />
      <Features />
      <Footer />
    </main>
  );
}
