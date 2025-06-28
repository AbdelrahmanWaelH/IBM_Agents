#!/usr/bin/env python3
"""
Test script for onboarding functionality
"""
import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_onboarding_chat():
    """Test the onboarding chat endpoint"""
    print("🧪 Testing onboarding chat...")
    
    # Test initial message
    payload = {
        "message": "Hi, I'm new to investing and want to learn more",
        "conversation_history": []
    }
    
    try:
        response = requests.post(f"{BASE_URL}/onboarding/chat", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response: {data['response'][:100]}...")
            print(f"   Is complete: {data['is_complete']}")
            return True
        else:
            print(f"❌ Chat failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat request failed: {e}")
        return False

def test_preferences_endpoint():
    """Test the preferences endpoint"""
    print("🧪 Testing preferences endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/onboarding/preferences", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Preferences: {data}")
            return True
        else:
            print(f"❌ Preferences failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Preferences request failed: {e}")
        return False

def test_save_preferences():
    """Test saving preferences"""
    print("🧪 Testing save preferences...")
    
    test_preferences = {
        "risk_tolerance": "moderate",
        "investment_goals": ["growth", "income"],
        "time_horizon": "medium",
        "sectors_of_interest": ["technology", "healthcare"],
        "budget_range": "medium",
        "experience_level": "beginner",
        "automated_trading_preference": "analysis_only"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/onboarding/save-preferences", json=test_preferences, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Preferences saved: {data['message']}")
            return True
        else:
            print(f"❌ Save preferences failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Save preferences request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting onboarding API tests...\n")
    
    # Test endpoints
    results = []
    results.append(test_preferences_endpoint())
    results.append(test_save_preferences())
    results.append(test_preferences_endpoint())  # Test again after saving
    results.append(test_onboarding_chat())
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! Onboarding system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the backend logs for details.")
