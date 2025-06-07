# Unified Account Curation Strategy: Weighted Scoring with Multi-Source Boost

## Overview

This strategy combines the outputs from the `graph_base`, `content_base`, and `engagement_base` account discovery methods to produce a single, ranked list of top GenAI Twitter accounts. The goal is to leverage the strengths of each individual strategy and prioritize accounts that are identified as valuable through multiple lenses.

The core approach is:
1.  **Load Candidates**: Ingest candidate accounts and their primary scores from each of the three foundational strategies.
2.  **Normalize Scores**: Bring the scores from different strategies onto a common scale (0-1).
3.  **Weighted Combination**: Calculate a global score for each account by taking a weighted average of its normalized scores from the contributing strategies.
4.  **Multi-Source Bonus**: Apply a bonus to the global score if an account is identified by more than one strategy, significantly boosting those with cross-strategy validation.
5.  **Final Ranking**: Sort accounts by their final global score to produce the curated list.

## Input Files

The `unified_score_calculator.py` script expects the following JSON output files from the other strategies to be present in their respective directories:

1.  **Graph-Based Candidates**:
    *   Path: `../graph_base/genai_following_nodes.json`
    *   Format: A JSON list of objects. Each object must contain:
        *   `handle`: The Twitter username.
        *   `display_name`: The display name.
        *   `pagerank_score`: The PageRank score (or another designated primary score from graph analysis).
    *   Example Snippet:
        ```json
        [
          {
            "account_id": "user123",
            "handle": "GenAI_Expert1",
            "display_name": "Dr. Gen Expert",
            "follower_count": 15000,
            "verified": true,
            "pagerank_score": 0.0015
          }
        ]
        ```

2.  **Content-Based Candidates**:
    *   Path: `../content_base/content_discovery_results/content_candidates.json`
    *   Format: A JSON dictionary where keys are usernames. Each value object must contain:
        *   `username`: The Twitter username.
        *   `display_name`: The display name.
        *   `overall_score`: The overall score from the content-based strategy.
    *   Example Snippet:
        ```json
        {
          "GenAI_Expert1": {
            "username": "GenAI_Expert1",
            "display_name": "Dr. Gen Expert",
            "overall_score": 0.85
            // ... other fields
          }
        }
        ```

3.  **Engagement-Based Candidates**:
    *   Path: `../engagement_base/engagement_discovery_results/engagement_candidates.json`
    *   Format: A JSON dictionary where keys are usernames. Each value object must contain:
        *   `username`: The Twitter username.
        *   `display_name`: The display name.
        *   `overall_engagement_score`: The overall score from the engagement-based strategy.
    *   Example Snippet:
        ```json
        {
          "GenAI_Expert1": {
            "username": "GenAI_Expert1",
            "display_name": "Dr. Gen Expert",
            "overall_engagement_score": 0.77
            // ... other fields
          }
        }
        ```

## Script: `unified_score_calculator.py`

### Key Parameters (configurable in the script):

*   `STRATEGY_WEIGHTS`: Weights assigned to each strategy's score in the global calculation.
    *   Default: `{'graph': 0.33, 'content': 0.34, 'engagement': 0.33}`
*   `MULTI_SOURCE_BONUSES`: Multiplicative bonuses applied if an account is found by multiple sources.
    *   Default: `{2: 1.2, 3: 1.5}` (1.2x bonus for 2 sources, 1.5x for 3 sources)
*   `GRAPH_SCORE_FIELD`: The field name in `genai_following_nodes.json` to be used as the graph strategy's primary score (e.g., `'pagerank_score'`).
*   `OUTPUT_FILENAME`: Name of the file for the final ranked list.
    *   Default: `final_curated_list.json`

### Logic:

1.  **Data Loading**: Loads candidates and their relevant scores from the three JSON files.
2.  **Data Aggregation**: Creates a master dictionary of all unique accounts, storing their original scores from each strategy.
3.  **Score Normalization**: For each strategy, normalizes its scores across all candidates to a 0-1 range using min-max scaling. This ensures scores are comparable.
4.  **Global Score Calculation**:
    *   For each account, calculates a weighted sum of its normalized scores from the strategies it was found by, using `STRATEGY_WEIGHTS`.
5.  **Multi-Source Bonus Application**:
    *   Counts how many strategies identified each account.
    *   Applies the corresponding bonus from `MULTI_SOURCE_BONUSES` to the global score.
6.  **Ranking**: Sorts accounts by their final global score in descending order.
7.  **Output**: Saves the ranked list to `final_curated_list.json`. Each entry includes the username, display name, normalized scores, original scores, number of sources, and the final global score.

## Output File

*   Path: `final_curated_list.json` (within the `unified_scoring` directory)
*   Format: A JSON list of objects, ranked by `final_global_score`.
*   Example Snippet:
    ```json
    [
      {
        "username": "GenAI_Expert1",
        "display_name": "Dr. Gen Expert",
        "normalized_graph_score": 0.95,
        "normalized_content_score": 0.88,
        "normalized_engagement_score": 0.92,
        "num_sources": 3,
        "global_score_before_bonus": 0.916,
        "final_global_score": 1.374,
        "contributing_scores": {
          "graph": 0.0015,
          "content": 0.85,
          "engagement": 0.77
        }
      },
      // ... other accounts
    ]
    ```

## How to Run

1.  Ensure the input JSON files are present in their correct locations (`../graph_base/`, `../content_base/content_discovery_results/`, `../engagement_base/engagement_discovery_results/`).
2.  Navigate to the `prototypes/account_discovery/unified_scoring/` directory.
3.  Run the script: `python unified_score_calculator.py`
4.  The output will be generated in `final_curated_list.json`.

## Future Considerations

*   **Graph Strategy Score**: The current script uses a single field (e.g., `pagerank_score`) from the graph data. A more sophisticated "overall graph score" could be pre-calculated within the `graph_base` strategy by combining multiple graph metrics (centrality, community influence, etc.) before being fed into this unified scorer.
*   **Advanced Normalization**: Explore other normalization techniques if min-max scaling has undesirable properties for the score distributions.
*   **Dynamic Weight/Bonus Tuning**: The weights and bonuses are currently hardcoded. These could be tuned based on evaluation of the output quality or even learned if a feedback mechanism is established.
*   **Thresholding**: Additional pre-filtering or post-filtering thresholds could be applied based on minimum normalized scores or number of sources.

## Testing

A test script is provided to validate the unified scoring implementation:

```bash
# Run the complete test (creates sample data and runs scoring)
python test_unified_scoring.py

# Only create sample data files for manual testing
python test_unified_scoring.py --create-data

# Clean up test files
python test_unified_scoring.py --cleanup
```

The test script creates sample data representing:
- **4 graph-based candidates** (Andrew Ng, OpenAI, Jim Fan, Yann LeCun)
- **3 content-based candidates** (Andrew Ng, OpenAI, Andrej Karpathy)  
- **4 engagement-based candidates** (OpenAI, Jim Fan, Andrej Karpathy, François Chollet)

This results in **5 unique accounts** with different source combinations:
- **OpenAI**: 3 sources (1.5x bonus)
- **Jim Fan, Andrej Karpathy**: 2 sources each (1.2x bonus)
- **Andrew Ng, Yann LeCun, François Chollet**: 1 source each (1.0x bonus)

The test validates proper scoring, normalization, and multi-source bonus application.

## Configuration

Key parameters can be adjusted in `unified_score_calculator.py`:

```python
# Strategy weights (should sum to 1.0)
STRATEGY_WEIGHTS = {
    'graph': 0.45,      # Graph-based discovery (following relationships)
    'content': 0.30,    # Content-based discovery (bio, tweets, topics)
    'engagement': 0.25  # Engagement-based discovery (replies, quotes, viral content)
}

# Multi-source bonuses
MULTI_SOURCE_BONUSES = {
    1: 1.0,  # No bonus for single source
    2: 1.2,  # 20% bonus for 2 sources  
    3: 1.5   # 50% bonus for 3 sources
}

# Graph score field to use
GRAPH_SCORE_FIELD = "pagerank_score"  # or "weighted_in_degree"
```

## Output Format

The final ranked list (`final_curated_list.json`) contains:

```json
[
  {
    "username": "openai",
    "display_name": "OpenAI", 
    "normalized_graph_score": 0.85,
    "normalized_content_score": 0.92,
    "normalized_engagement_score": 0.78,
    "num_sources": 3,
    "global_score_before_bonus": 0.8435,
    "final_global_score": 1.2653,
    "contributing_scores": {
      "graph": 0.92,
      "content": 0.94,
      "engagement": 0.87
    }
  }
]
``` 