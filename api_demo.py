#!/usr/bin/env python3
"""
Demonstration script for the Option Comparison Tool API.

This script shows how to use the REST API to create comparisons,
run analysis, and export results.
"""

import requests
import json
import time
from typing import Dict, Any


def demo_api():
    """Demonstrate the API functionality."""
    base_url = "http://localhost:8000"
    
    print("🚀 Option Comparison Tool API Demo")
    print("=" * 50)
    
    # Check health
    print("\n1. Health Check")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        health_data = response.json()
        print(f"✅ API is healthy (version: {health_data['version']})")
    else:
        print("❌ API is not responding")
        return
    
    # Create a comparison session
    print("\n2. Creating Comparison Session")
    session_data = {
        "options": [
            {
                "name": "Cloud Provider A",
                "description": "Major cloud provider with global presence",
                "attributes": {
                    "Cost": 100,
                    "Performance": 9,
                    "Reliability": 0.99,
                    "Support": 8
                }
            },
            {
                "name": "Cloud Provider B",
                "description": "Cost-effective cloud solution",
                "attributes": {
                    "Cost": 60,
                    "Performance": 7,
                    "Reliability": 0.95,
                    "Support": 6
                }
            },
            {
                "name": "Cloud Provider C",
                "description": "High-performance specialized provider",
                "attributes": {
                    "Cost": 150,
                    "Performance": 10,
                    "Reliability": 0.98,
                    "Support": 9
                }
            }
        ],
        "constraints": [
            {
                "name": "Cost",
                "description": "Monthly cost in dollars",
                "weight": 0.3,
                "type": "numeric",
                "priority": "required"
            },
            {
                "name": "Performance",
                "description": "Performance rating (1-10)",
                "weight": 0.4,
                "type": "numeric",
                "priority": "required"
            },
            {
                "name": "Reliability",
                "description": "Uptime reliability (0-1)",
                "weight": 0.2,
                "type": "numeric",
                "priority": "preferred"
            },
            {
                "name": "Support",
                "description": "Support quality rating (1-10)",
                "weight": 0.1,
                "type": "numeric",
                "priority": "nice-to-have"
            }
        ]
    }
    
    response = requests.post(f"{base_url}/sessions", json=session_data)
    if response.status_code == 201:
        session = response.json()
        session_id = session["id"]
        print(f"✅ Created session: {session_id}")
        print(f"   Options: {len(session['options'])}")
        print(f"   Constraints: {len(session['constraints'])}")
    else:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.text)
        return
    
    # Run analysis
    print("\n3. Running Analysis")
    analysis_request = {"method": "weighted_scoring"}
    response = requests.post(f"{base_url}/sessions/{session_id}/analyze", json=analysis_request)
    
    if response.status_code == 200:
        analysis_data = response.json()
        print("✅ Analysis completed")
        
        # Display results if available
        if "results" in analysis_data and "scoring_results" in analysis_data["results"]:
            scoring_results = analysis_data["results"]["scoring_results"]
            if hasattr(scoring_results, 'option_scores') or 'option_scores' in scoring_results:
                print("\n📊 Results:")
                option_scores = scoring_results.get('option_scores', [])
                for i, score in enumerate(option_scores[:3]):  # Show top 3
                    if isinstance(score, dict):
                        print(f"   {i+1}. {score.get('option_name', 'Unknown')}: {score.get('total_score', 0):.3f}")
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        print(response.text)
    
    # Test weight adjustment
    print("\n4. Testing Weight Adjustment")
    weight_adjustments = {
        "weight_adjustments": {
            "Cost": 0.5,  # Increase cost importance
            "Performance": 0.3  # Decrease performance importance
        }
    }
    
    response = requests.post(f"{base_url}/sessions/{session_id}/adjust-weights", json=weight_adjustments)
    if response.status_code == 200:
        impact_data = response.json()
        print("✅ Weight adjustment completed")
        print(f"   Most affected options: {len(impact_data.get('most_affected_options', []))}")
        print(f"   Ranking changes: {len(impact_data.get('ranking_changes', []))}")
    else:
        print(f"❌ Weight adjustment failed: {response.status_code}")
    
    # Test what-if scenario
    print("\n5. Creating What-If Scenario")
    scenario_data = {
        "scenario_name": "Cost-Focused Analysis",
        "weight_adjustments": {
            "Cost": 0.6,
            "Performance": 0.2,
            "Reliability": 0.1,
            "Support": 0.1
        }
    }
    
    response = requests.post(f"{base_url}/sessions/{session_id}/what-if", json=scenario_data)
    if response.status_code == 200:
        scenario_result = response.json()
        print("✅ What-if scenario created")
        print(f"   Scenario: {scenario_result['scenario_name']}")
        print(f"   Ranking changes: {len(scenario_result.get('ranking_changes', []))}")
    else:
        print(f"❌ What-if scenario failed: {response.status_code}")
    
    # List templates
    print("\n6. Listing Available Templates")
    response = requests.get(f"{base_url}/templates")
    if response.status_code == 200:
        templates = response.json()
        print(f"✅ Found {len(templates)} templates")
        for template in templates[:3]:  # Show first 3
            print(f"   - {template['name']}: {template['description']}")
    else:
        print(f"❌ Failed to list templates: {response.status_code}")
    
    # Clean up
    print("\n7. Cleanup")
    response = requests.delete(f"{base_url}/sessions/{session_id}")
    if response.status_code == 200:
        print("✅ Session deleted")
    else:
        print(f"⚠️  Failed to delete session: {response.status_code}")
    
    print("\n🎉 Demo completed successfully!")
    print("\nTo explore more:")
    print(f"- API Documentation: {base_url}/docs")
    print(f"- ReDoc Documentation: {base_url}/redoc")


if __name__ == "__main__":
    try:
        demo_api()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server.")
        print("Please start the server first:")
        print("  option-compare-api")
        print("  # or")
        print("  python -m option_comparison_tool.api_server")
    except Exception as e:
        print(f"❌ Demo failed: {e}")