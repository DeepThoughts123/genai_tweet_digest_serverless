"""
Prompt templates for tweet categorization using Gemini 2.0 Flash
"""

TWEET_CATEGORIZATION_PROMPT = """
You are an expert AI content categorizer specializing in GenAI/AI/ML content classification.

Your task is to categorize the following tweet summary into one of the existing categories OR create a new category if none of the existing categories fit well.

EXISTING CATEGORIES:
{categories_list}

TWEET SUMMARY TO CATEGORIZE:
"{tweet_summary}"

INSTRUCTIONS:
1. Analyze the tweet summary carefully to understand its main topic and intent
2. First, try to match it to one of the existing categories above
3. If the tweet fits well into an existing category, use that category name EXACTLY as listed
4. If none of the existing categories are a good fit, create a NEW category name that would be appropriate
5. New categories should follow the same naming convention (title case, descriptive)
6. New categories should be broad enough to accommodate similar future tweets

RESPONSE FORMAT:
Respond in JSON format only:
{{
  "category": "Selected or New Category Name",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this category was chosen",
  "is_new_category": true|false,
  "suggested_description": "If new category, provide a description similar to existing ones"
}}

EXAMPLES:
- For a tweet about "OpenAI releases GPT-5 with new capabilities": category would be "Product Announcements"
- For a tweet about "How to fine-tune LLMs: A beginner's guide": category would be "Tutorials & Education"  
- For a tweet about "New paper on transformer efficiency published at ICLR": category would be "Research & Papers"

Ensure your response is valid JSON with no additional text.
"""

def build_categorization_prompt(categories_data: dict, tweet_summary: str) -> str:
    """
    Build the categorization prompt with current categories and tweet summary.
    
    Args:
        categories_data: Dictionary containing categories from JSON file
        tweet_summary: Summary text from tweet metadata
        
    Returns:
        Formatted prompt string for Gemini API
    """
    # Format categories list for the prompt
    categories_list = ""
    for i, category in enumerate(categories_data.get("categories", []), 1):
        categories_list += f"{i}. {category['name']}: {category['description']}\n"
    
    return TWEET_CATEGORIZATION_PROMPT.format(
        categories_list=categories_list.strip(),
        tweet_summary=tweet_summary
    ).strip() 