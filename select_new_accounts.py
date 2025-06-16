#!/usr/bin/env python3
import random
import csv

def select_fresh_accounts():
    """Select 8 new accounts (2 from each category) for end-to-end testing."""
    
    # Read the CSV file
    accounts = []
    with open('tmp/twitter_accounts_100.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append(row)

    # Separate by category
    categories = {}
    for account in accounts:
        category = account['type']
        if category not in categories:
            categories[category] = []
        categories[category].append(account)

    # Previously selected accounts to avoid
    previous_accounts = {
        'fchollet', 'gdb', 'LuisSerrano', 'jackclarksf', 
        'cohere', 'MSFTResearch', 'theneurondaily', 'bensbitesdaily'
    }

    # Select 2 from each category, avoiding previous selections
    selected = []
    target_categories = ['research_leader', 'builder', 'company', 'newsletter']
    
    print("🎯 Selecting fresh set of 8 accounts for end-to-end test...")
    
    for category in target_categories:
        if category in categories:
            # Filter out previously selected accounts
            available = [acc for acc in categories[category] 
                        if acc['handle'].replace('@', '') not in previous_accounts]
            
            if len(available) >= 2:
                selected_for_category = random.sample(available, 2)
                selected.extend(selected_for_category)
                print(f"\n{category.upper()}:")
                for acc in selected_for_category:
                    print(f"  • {acc['handle']:20} {acc['name']}")
            else:
                print(f"⚠️  Not enough available accounts in {category} category")

    print(f"\n📋 Selected {len(selected)} accounts total")
    print("\n🔗 Handles for processing:")
    handles = [account["handle"].replace('@', '') for account in selected]
    print(' '.join(handles))
    
    return handles

if __name__ == "__main__":
    fresh_accounts = select_fresh_accounts()
    
    print(f"\n✅ Ready for end-to-end test with {len(fresh_accounts)} accounts") 