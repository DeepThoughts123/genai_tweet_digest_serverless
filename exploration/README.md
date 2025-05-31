# Exploration Lab 🧪

This folder contains experimental scripts for testing and exploring ideas with the GenAI Tweets Digest project. All scripts use the same `tweet_services.py` infrastructure as the production Lambda functions.

## Quick Start

### 1. Install Dependencies
```bash
# From the project root
cd lambdas
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
```bash
cd exploration

# Copy the template and create your .env file
cp env_template.txt .env

# Edit .env with your actual API credentials
# Required: TWITTER_BEARER_TOKEN
# Optional: GEMINI_API_KEY (for AI features)
```

### 3. Run Your Experiments
```bash
# Comprehensive testing
python tweet_fetching_experiments.py

# Quick testing
python quick_tweet_test.py
```

## Scripts Available

### 🚀 `tweet_fetching_experiments.py`
**Comprehensive exploration script with multiple test scenarios**

Features:
- Single account tweet fetching
- Multiple accounts with stats comparison  
- AI-powered tweet categorization (requires Gemini API)
- Full pipeline testing (fetch → categorize → summarize)
- Time range analysis for understanding tweet patterns
- Interactive custom account testing
- Results saving functionality

### ⚡ `quick_tweet_test.py`
**Minimal script for rapid testing**

Perfect for quick tests and iterations when you just want to fetch a few tweets without all the bells and whistles.

## Environment Configuration

All scripts automatically load environment variables from a `.env` file in this directory. 

### Setting Up Your .env File

1. **Copy the template:**
   ```bash
   cp env_template.txt .env
   ```

2. **Edit `.env` with your API credentials:**
   ```bash
   # Required for basic tweet fetching
   TWITTER_BEARER_TOKEN=your_actual_twitter_bearer_token

   # Optional for AI categorization and summarization
   GEMINI_API_KEY=your_actual_gemini_api_key

   # Optional AWS settings (for S3 operations)
   S3_BUCKET=your-test-bucket
   AWS_REGION=us-east-1
   ```

3. **Get your API keys:**
   - **Twitter Bearer Token**: https://developer.twitter.com/en/portal/dashboard
   - **Gemini API Key**: https://ai.google.dev/

### Alternative: Environment Variables
You can also set environment variables directly:
```bash
export TWITTER_BEARER_TOKEN="your_actual_token"
export GEMINI_API_KEY="your_actual_key"
```

## What You Can Test

### 🐦 Tweet Fetching
- Different Twitter accounts and usernames
- Various time ranges (1 day, 1 week, 2 weeks, etc.)
- Different tweet limits per user
- Error handling for non-existent accounts
- Rate limiting behavior

### 🤖 AI Processing (with Gemini API key)
- Tweet categorization accuracy
- Category confidence scores
- Summary generation quality
- Full pipeline performance

### 📊 Analytics & Insights
- Engagement metrics (likes, retweets)
- Tweet volume patterns over time
- Most popular tweets identification
- Account comparison analysis

## Available Tweet Services

The scripts use these classes from `../lambdas/shared/tweet_services.py`:

- **`TweetFetcher`**: Fetches tweets using Twitter API v2
- **`TweetCategorizer`**: AI-powered categorization using Gemini
- **`TweetSummarizer`**: Generates summaries by category
- **`S3DataManager`**: Saves results to S3 (optional)

## Tips for Exploration

### Start Small
```python
# Test with just 1-2 tweets first
tweets = fetcher.fetch_tweets(["username"], days_back=1, max_tweets_per_user=2)
```

### Save Interesting Results
```python
# Use the built-in save function
save_exploration_results(tweets, "my_experiment_results.json")
```

### Monitor API Usage
- Twitter API has rate limits
- Gemini API has usage quotas
- Start with small test batches

### Experiment Ideas
1. **Compare AI accounts**: Test different influential AI accounts to see content patterns
2. **Time sensitivity**: Compare weekday vs weekend tweet patterns
3. **Engagement analysis**: Find what types of tweets get the most engagement
4. **Category accuracy**: Test how well the AI categorization works on different topics
5. **Content trends**: Track how topics evolve over time

## File Organization

```
exploration/
├── README.md                     # This file
├── env_template.txt              # Template for .env file
├── .env                          # Your API credentials (create this)
├── tweet_fetching_experiments.py # Comprehensive exploration
├── quick_tweet_test.py           # Minimal quick testing
├── results/                      # Save your experiment results here
└── [your_custom_scripts.py]      # Add your own experiments
```

## Integration with Main Project

These scripts use the exact same:
- Configuration patterns (`../lambdas/shared/config.py`)
- Tweet processing logic (`../lambdas/shared/tweet_services.py`)
- Error handling and API integration

Results and insights from exploration can directly inform production improvements!

## Troubleshooting

**Missing .env file:**
```
❌ Please set your TWITTER_BEARER_TOKEN environment variable
   Create a .env file in this directory with your API credentials
```
**Solution:** Copy `env_template.txt` to `.env` and add your API keys.

**Import Errors:**
Make sure you're running from the `exploration/` directory:
```bash
cd exploration
python script_name.py
```

**API Errors:**
- Check your credentials are valid and properly formatted in `.env`
- Verify rate limits aren't exceeded
- Ensure your Twitter account has API access

**No Tweets Found:**
- Try different usernames (some accounts tweet rarely)
- Expand the time range (`days_back` parameter)
- Check if the account exists and has recent public tweets

---

Happy exploring! 🚀 