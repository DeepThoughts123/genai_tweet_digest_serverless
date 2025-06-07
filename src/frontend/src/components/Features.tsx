const features = [
  {
    icon: '🎯',
    title: 'Curated Content',
    description: 'Hand-picked tweets from 200+ influential AI researchers, engineers, and thought leaders in the GenAI space.'
  },
  {
    icon: '🤖',
    title: 'AI-Powered Analysis',
    description: 'Advanced categorization and summarization using Gemini 2.0 Flash to extract key insights and trends.'
  },
  {
    icon: '📊',
    title: 'Organized Categories',
    description: 'Content sorted into logical categories: model releases, research findings, applications, ethics, and tools.'
  },
  {
    icon: '⚡',
    title: 'Weekly Digest',
    description: 'Receive a comprehensive summary every week, saving you hours of scrolling through social media.'
  },
  {
    icon: '🎓',
    title: 'For All Levels',
    description: 'Whether you\'re a beginner or expert, our summaries are crafted to be accessible and informative.'
  },
  {
    icon: '🔒',
    title: 'Privacy First',
    description: 'No spam, no data selling. Just valuable AI insights delivered directly to your inbox.'
  }
];

export default function Features() {
  return (
    <section className="bg-white py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Why Choose GenAI Tweets Digest?
          </h2>
          <p className="mt-6 text-lg leading-8 text-gray-600">
            Stay informed about the rapidly evolving AI landscape without the noise. 
            Get the signal that matters, when it matters.
          </p>
        </div>
        
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
            {features.map((feature, index) => (
              <div key={index} className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <span className="text-2xl">{feature.icon}</span>
                  {feature.title}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">{feature.description}</p>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
} 