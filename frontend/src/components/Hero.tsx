import EmailSignup from './EmailSignup';

interface HeroProps {
  onSubscribe?: (email: string) => void;
}

export default function Hero({ onSubscribe }: HeroProps = {}) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-purple-50 px-6 py-24 sm:py-32 lg:px-8">
      <div className="mx-auto max-w-4xl text-center">
        {/* Badge */}
        <div className="mb-8 inline-flex items-center rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-800">
          <span className="mr-2">🤖</span>
          Weekly AI Insights Delivered
        </div>

        {/* Main Heading */}
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl lg:text-7xl">
          Stay Ahead of the{' '}
          <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Revolution
          </span>
        </h1>

        {/* Subheading */}
        <p className="mt-6 text-lg leading-8 text-gray-600 sm:text-xl">
          Get the most impactful Generative AI content from Twitter, curated and summarized 
          into digestible insights. From breakthrough research to trending discussions—delivered 
          weekly to your inbox.
        </p>

        {/* Features List */}
        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
            <span className="text-green-500">✓</span>
            <span>Curated from 200+ AI experts</span>
          </div>
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
            <span className="text-green-500">✓</span>
            <span>AI-powered categorization</span>
          </div>
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
            <span className="text-green-500">✓</span>
            <span>Weekly digest format</span>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-12">
          <EmailSignup onSubscribe={onSubscribe} />
        </div>

        {/* Social Proof */}
        <p className="mt-6 text-sm text-gray-500">
          Join thousands of AI enthusiasts, researchers, and professionals
        </p>
      </div>

      {/* Background Decoration */}
      <div className="absolute inset-x-0 top-[calc(100%-13rem)] -z-10 transform-gpu overflow-hidden blur-3xl sm:top-[calc(100%-30rem)]">
        <div className="relative left-[calc(50%+3rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 bg-gradient-to-tr from-blue-300 to-purple-300 opacity-20 sm:left-[calc(50%+36rem)] sm:w-[72.1875rem]" />
      </div>
    </section>
  );
} 