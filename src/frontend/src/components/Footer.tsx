export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-900">
      <div className="mx-auto max-w-7xl px-6 py-12 md:flex md:items-center md:justify-between lg:px-8">
        <div className="flex justify-center space-x-6 md:order-2">
          <a
            href="#"
            className="text-gray-400 hover:text-gray-300 transition-colors duration-200"
          >
            <span className="sr-only">Privacy Policy</span>
            Privacy
          </a>
          <a
            href="#"
            className="text-gray-400 hover:text-gray-300 transition-colors duration-200"
          >
            <span className="sr-only">Terms of Service</span>
            Terms
          </a>
          <a
            href="#"
            className="text-gray-400 hover:text-gray-300 transition-colors duration-200"
          >
            <span className="sr-only">Contact</span>
            Contact
          </a>
        </div>
        <div className="mt-8 md:order-1 md:mt-0">
          <div className="flex items-center justify-center md:justify-start">
            <span className="text-2xl mr-2">🤖</span>
            <span className="text-white font-semibold">GenAI Tweets Digest</span>
          </div>
          <p className="text-center text-xs leading-5 text-gray-400 md:text-left mt-2">
            &copy; {currentYear} GenAI Tweets Digest. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
} 