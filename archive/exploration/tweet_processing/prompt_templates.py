TWEET_TEXT_EXTRACTION_PROMPT = """
Please analyze the provided tweet screenshot(s) and extract the following information:

1. COMPLETE TEXT EXTRACTION:
   - Identify the main tweet being analyzed in the screenshot(s). Extract all its textual content.
   - Reproduce the original wording, punctuation, and line breaks as faithfully as possible.
   - If the tweet's text spans multiple screenshots, combine these parts in their correct order to form a single, continuous text.
   - Focus strictly on the content of this single, main tweet. Do not include the text of replies or comments from other users, even if they are visible in the screenshots.

2. SUMMARY GENERATION:
   - Create a concise 1-2 sentence summary that captures the key information and main point of the tweet
   - Focus on the core message, findings, announcements, or insights
   - Keep it informative but brief, suitable for a digest format

3. ENGAGEMENT METRICS:
   - Extract the number of replies, retweets, likes, and bookmarks (saves) of the tweet if they are visible in the screenshots
   - If the engagement metrics are not visible in the screenshots, use null values

Please respond in the following JSON format strictly and nothing else:
{
  "full_text": "Complete extracted text from the tweet...",
  "summary": "Concise 1-2 sentence summary of the tweet content...",
  "reply_count": "Number of replies to the tweet",
  "retweet_count": "Number of retweets of the tweet",
  "like_count": "Number of likes of the tweet",
  "bookmark_count": "Number of bookmarks (saves) of the tweet"
}

Ensure the JSON is valid and properly formatted. If you cannot extract text or generate a summary or identify the engagement metrics, use null values.
"""