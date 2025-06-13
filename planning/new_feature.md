I need to develop a feature to compile a list of influential Twitter accounts in the generative AI field. Here's how the feature will function:

- Begin with a set of initial seed URLs.
- For each URL, perform the following steps:
  - Capture an image of the page and extract the user's profile description, number of followers, and number of following from the image.
  - Use the Gemini model to classify the profile description and determine if the user is active in the generative AI space. Skip users who are not active.
  - For active users, construct a new URL leading to their "following" page.
  - On the "following" page, scroll down to capture images of the entire page.
  - Use the Gemini model to extract the handles of accounts followed by the user from these images.
  - Create a new list of URLs based on these handles, representing the profile pages of the users being followed.
  - Add this new list to the queue of URLs to be processed.
- Repeat this process for N iterations. The seed URLs represent iteration 0, URLs generated from iteration 0 represent iteration 1, and so on. The user can set the value of N.

- By the end of the process, you should have a list of Twitter accounts with user handles, profile descriptions, and follower/following counts.

All image capturing should be done using Selenium with headless Chrome.