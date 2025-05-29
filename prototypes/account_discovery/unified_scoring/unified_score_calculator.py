#!/usr/bin/env python3
"""
Unified Score Calculator for GenAI Twitter Account Discovery

This script combines candidate accounts from graph, content, and engagement
strategies, normalizes their scores, applies weighted averaging and multi-source
bonuses, and produces a final ranked list.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Any

# --- Configuration ---
GRAPH_CANDIDATES_FILE = os.path.join("..", "graph_base", "genai_following_nodes.json")
CONTENT_CANDIDATES_FILE = os.path.join("..", "content_base", "content_discovery_results", "content_candidates.json")
ENGAGEMENT_CANDIDATES_FILE = os.path.join("..", "engagement_base", "engagement_discovery_results", "engagement_candidates.json")

OUTPUT_FILENAME = "final_curated_list.json"

# Field from graph_base/genai_following_nodes.json to use as the score
# Common choices: 'pagerank_score', 'weighted_in_degree'
GRAPH_SCORE_FIELD = "pagerank_score" 

STRATEGY_WEIGHTS = {
    'graph': 0.45,
    'content': 0.30,
    'engagement': 0.25
}

MULTI_SOURCE_BONUSES = {
    1: 1.0,  # No bonus for a single source
    2: 1.2,  # 20% bonus for 2 sources
    3: 1.5   # 50% bonus for 3 sources
}

# Target number of accounts in the final list (for display purposes, script outputs all ranked)
TARGET_LIST_SIZE = 300

# --- Helper Functions ---

def load_json_file(filepath: str) -> Any:
    """Load data from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found - {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {filepath}: {e}")
        return None

def normalize_scores(accounts_data: Dict[str, Dict[str, float]], score_field_name: str) -> None:
    """Normalize scores for a given strategy using min-max scaling (0-1)."""
    # Extract strategy name from score field name (remove '_score' suffix)
    strategy_name = score_field_name.replace('_score', '')
    
    scores = [data.get(score_field_name, 0) for data in accounts_data.values() 
              if score_field_name in data and data[score_field_name] is not None]
    if not scores:
        print(f"No scores found for strategy {strategy_name} to normalize.")
        # Assign 0 to all normalized scores if no original scores exist or all are None
        for username in accounts_data:
            accounts_data[username][f'normalized_{strategy_name}_score'] = 0.0
        return

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        # All scores are the same, normalize to 0.5 (or 0 or 1, depending on preference)
        # or handle as a special case, e.g., if all are 0, normalized is 0.
        normalized_value = 0.5 if max_score != 0 else 0.0 
        for username in accounts_data:
            if score_field_name in accounts_data[username] and accounts_data[username][score_field_name] is not None:
                accounts_data[username][f'normalized_{strategy_name}_score'] = normalized_value
            else:
                accounts_data[username][f'normalized_{strategy_name}_score'] = 0.0 # Handle None scores
    else:
        for username in accounts_data:
            if score_field_name in accounts_data[username] and accounts_data[username][score_field_name] is not None:
                original_score = accounts_data[username][score_field_name]
                normalized = (original_score - min_score) / (max_score - min_score)
                accounts_data[username][f'normalized_{strategy_name}_score'] = normalized
            else:
                 accounts_data[username][f'normalized_{strategy_name}_score'] = 0.0 # Handle None scores

# --- Main Processing Logic ---

def main():
    """Main function to orchestrate the unified scoring process."""
    print("Starting unified account curation...")

    # 1. Load candidate data from all strategies
    graph_candidates_raw = load_json_file(GRAPH_CANDIDATES_FILE)
    content_candidates_raw = load_json_file(CONTENT_CANDIDATES_FILE)
    engagement_candidates_raw = load_json_file(ENGAGEMENT_CANDIDATES_FILE)

    if graph_candidates_raw is None or content_candidates_raw is None or engagement_candidates_raw is None:
        print("One or more input files could not be loaded. Exiting.")
        return

    # 2. Aggregate accounts and their original scores
    # Master dictionary: {username: {'display_name': str, 'graph_score': float, ...}}
    aggregated_accounts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        'graph_score': None, 
        'content_score': None, 
        'engagement_score': None,
        'display_name': None,
        'num_sources': 0
    })

    print("Aggregating candidates from all sources...")
    # Process Graph-Based Candidates (List of Dicts)
    for acc in graph_candidates_raw:
        username = acc.get('handle')
        if not username:
            continue
        aggregated_accounts[username]['graph_score'] = acc.get(GRAPH_SCORE_FIELD)
        if aggregated_accounts[username]['display_name'] is None:
             aggregated_accounts[username]['display_name'] = acc.get('display_name')
        if acc.get(GRAPH_SCORE_FIELD) is not None: # Count source only if score is present
            aggregated_accounts[username]['sources_temp'] = aggregated_accounts[username].get('sources_temp', set()).union({'graph'})

    # Process Content-Based Candidates (Dict of Dicts)
    for username, acc_data in content_candidates_raw.items():
        aggregated_accounts[username]['content_score'] = acc_data.get('overall_score')
        if aggregated_accounts[username]['display_name'] is None:
             aggregated_accounts[username]['display_name'] = acc_data.get('display_name')
        if acc_data.get('overall_score') is not None:
            aggregated_accounts[username]['sources_temp'] = aggregated_accounts[username].get('sources_temp', set()).union({'content'})

    # Process Engagement-Based Candidates (Dict of Dicts)
    for username, acc_data in engagement_candidates_raw.items():
        aggregated_accounts[username]['engagement_score'] = acc_data.get('overall_engagement_score')
        if aggregated_accounts[username]['display_name'] is None:
             aggregated_accounts[username]['display_name'] = acc_data.get('display_name')
        if acc_data.get('overall_engagement_score') is not None:
            aggregated_accounts[username]['sources_temp'] = aggregated_accounts[username].get('sources_temp', set()).union({'engagement'})
            
    # Finalize num_sources
    for username in aggregated_accounts:
        aggregated_accounts[username]['num_sources'] = len(aggregated_accounts[username].get('sources_temp', set()))
        if 'sources_temp' in aggregated_accounts[username]:
            del aggregated_accounts[username]['sources_temp'] # cleanup temp field

    print(f"Aggregated {len(aggregated_accounts)} unique accounts.")

    # 3. Normalize scores for each strategy
    print("Normalizing scores...")
    normalize_scores(aggregated_accounts, 'graph_score')
    normalize_scores(aggregated_accounts, 'content_score')
    normalize_scores(aggregated_accounts, 'engagement_score')

    # 4. Calculate global scores and apply bonuses
    print("Calculating global scores and applying multi-source bonuses...")
    final_ranked_list = []
    for username, data in aggregated_accounts.items():
        global_score = 0
        num_sources = data['num_sources']
        contributing_scores = {}

        # Weighted sum of normalized scores
        if data['normalized_graph_score'] is not None and data['graph_score'] is not None:
            global_score += data['normalized_graph_score'] * STRATEGY_WEIGHTS['graph']
            contributing_scores['graph'] = data['graph_score']
        if data['normalized_content_score'] is not None and data['content_score'] is not None:
            global_score += data['normalized_content_score'] * STRATEGY_WEIGHTS['content']
            contributing_scores['content'] = data['content_score']
        if data['normalized_engagement_score'] is not None and data['engagement_score'] is not None:
            global_score += data['normalized_engagement_score'] * STRATEGY_WEIGHTS['engagement']
            contributing_scores['engagement'] = data['engagement_score']
        
        # In case of missing scores from some strategies, the weight effectively redistributes
        # For a more explicit redistribution, total_active_weight would be sum of weights for active sources
        # current_total_weight = sum(STRATEGY_WEIGHTS[s] for s in contributing_scores.keys())
        # if current_total_weight > 0 and current_total_weight < sum(STRATEGY_WEIGHTS.values()):
        #     global_score = (global_score / current_total_weight) # Normalize by active weights

        global_score_before_bonus = global_score
        
        # Apply multi-source bonus
        bonus_multiplier = MULTI_SOURCE_BONUSES.get(num_sources, 1.0)
        final_global_score = global_score_before_bonus * bonus_multiplier

        final_ranked_list.append({
            'username': username,
            'display_name': data.get('display_name', 'N/A'),
            'normalized_graph_score': data['normalized_graph_score'],
            'normalized_content_score': data['normalized_content_score'],
            'normalized_engagement_score': data['normalized_engagement_score'],
            'num_sources': num_sources,
            'global_score_before_bonus': round(global_score_before_bonus, 4),
            'final_global_score': round(final_global_score, 4),
            'contributing_scores': contributing_scores
        })

    # 5. Rank accounts
    final_ranked_list.sort(key=lambda x: x['final_global_score'], reverse=True)

    # 6. Save the final list
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(final_ranked_list, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved final curated list to {OUTPUT_FILENAME}")
    except IOError as e:
        print(f"Error saving results to {OUTPUT_FILENAME}: {e}")
    
    print(f"--- Top {min(20, len(final_ranked_list))} accounts ---")
    for i, acc in enumerate(final_ranked_list[:20]):
        print(f"{i+1}. @{acc['username']} (Score: {acc['final_global_score']:.4f}, Sources: {acc['num_sources']}) - Graph: {acc['normalized_graph_score']:.2f}, Content: {acc['normalized_content_score']:.2f}, Engagement: {acc['normalized_engagement_score']:.2f}")

if __name__ == "__main__":
    main() 