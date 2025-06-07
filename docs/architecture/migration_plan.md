I’ve built an app with several features: it fetches tweets from selected Twitter accounts weekly, uses an LLM to process and summarize the content, and then emails the summaries to a list of subscribers.

Initially, I designed the app as an AWS-hosted service that runs on a weekly schedule. I later migrated it to AWS Lambda, thinking it would be a better fit. However, I’ve since run into a limitation: Lambda functions have a maximum runtime of 15 minutes, and one part of my app—extracting tweet content using a Selenium browser-based approach—can take much longer. This process involves capturing images and processing tweets one by one, and I expect it could take a few hours in some cases.

Given this constraint, I’m no longer sure Lambda is the right choice for this architecture.

Here's what I’d like you to do:

- Review the current implementation and documentation.

- Understand the architecture and where things stand.

- Assess whether Lambda is still a viable solution given the long-running nature of the tweet extraction step.

- If not, consider whether we should switch to an EC2-based approach.

- If EC2 is the better fit, please advise how we can adapt the current codebase to support that transition.

Make sure you first read carefully the product_requirement_document.md and all the documents in the ./docs directory as well as the ./exploration directory (which contains some features I plan to integrate into the app) to undertstand features that have been implemented as well as the codebase structure.