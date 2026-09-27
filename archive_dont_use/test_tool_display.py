#!/usr/bin/env python3
"""
Test script for the enhanced tool display functions
"""

import json
from chainapp import get_tool_icon, format_search_results, format_provider_results

def test_tool_icons():
    """Test tool icon mapping"""
    print("Testing tool icons:")
    tools = ["tmdb_search_movie", "tmdb_watch_providers", "tmdb_search_tv", "tmdb_tv_watch_providers", "unknown_tool"]
    for tool in tools:
        icon = get_tool_icon(tool)
        print(f"  {tool}: {icon}")
    print()

def test_search_results():
    """Test search results formatting"""
    print("Testing search results formatting:")
    
    # Test empty results
    empty_result = format_search_results([])
    print(f"  Empty: {empty_result}")
    
    # Test single result
    single_result = format_search_results([{"title": "Inception", "release_year": "2010", "id": 27205}])
    print(f"  Single: {single_result}")
    
    # Test multiple results
    multiple_results = format_search_results([
        {"title": "Inception", "release_year": "2010", "id": 27205},
        {"title": "The Dark Knight", "release_year": "2008", "id": 155},
        {"title": "Interstellar", "release_year": "2014", "id": 157336},
        {"title": "Dunkirk", "release_year": "2017", "id": 373571},
        {"title": "Tenet", "release_year": "2020", "id": 577922}
    ])
    print(f"  Multiple: {multiple_results}")
    print()

def test_provider_results():
    """Test provider results formatting"""
    print("Testing provider results formatting:")
    
    # Test empty providers
    empty_providers = format_provider_results({})
    print(f"  Empty: {empty_providers}")
    
    # Test sample provider data
    sample_providers = {
        "US": {
            "flatrate": [
                {"provider_name": "Netflix", "provider_id": 8},
                {"provider_name": "Hulu", "provider_id": 15}
            ]
        },
        "GB": {
            "flatrate": [
                {"provider_name": "Netflix", "provider_id": 8},
                {"provider_name": "Amazon Prime", "provider_id": 119}
            ]
        },
        "CA": {
            "flatrate": [
                {"provider_name": "Crave", "provider_id": 230}
            ]
        }
    }
    
    provider_result = format_provider_results(sample_providers)
    print(f"  Sample: {provider_result}")
    print()

if __name__ == "__main__":
    print("🧪 Testing Enhanced Tool Display Functions\n")
    test_tool_icons()
    test_search_results()
    test_provider_results()
    print("✅ All tests completed!")