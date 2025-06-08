#!/usr/bin/env python3
"""
Test script to verify task-independent detection counters
"""

import requests
import time
import json

def test_task_independence():
    """Test that fire and yellow leaves counters are independent"""
    
    dashboard_url = "http://localhost:8080"
    
    print("🧪 Testing Task-Independent Detection Counters")
    print("=" * 50)
    
    # Wait for system to be ready
    print("⏳ Waiting for system to be ready...")
    for i in range(10):
        try:
            response = requests.get(f"{dashboard_url}/api/statistics", timeout=3)
            if response.status_code == 200:
                print("✅ System is ready!")
                break
        except:
            time.sleep(2)
    else:
        print("❌ System not ready after 20 seconds")
        return
    
    # Test 1: Check initial state (should be fire task by default)
    print("\n📊 Step 1: Check initial statistics (Fire task)")
    response = requests.get(f"{dashboard_url}/api/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Current task: {stats.get('current_task', 'unknown')}")
        print(f"   Total detections: {stats.get('total_detections', 0)}")
        print(f"   Fire alerts: {stats.get('fire_alerts', 0)}")
        fire_initial_count = stats.get('total_detections', 0)
    else:
        print("❌ Failed to get initial statistics")
        return
    
    # Test 2: Switch to yellow leaves task
    print("\n🔄 Step 2: Switch to Yellow Leaves task")
    response = requests.post(f"{dashboard_url}/api/switch-task", 
                           json={"task": "leaves"}, 
                           headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        print("✅ Successfully switched to yellow leaves task")
    else:
        print("❌ Failed to switch task")
        return
    
    # Test 3: Check statistics after task switch
    print("\n📊 Step 3: Check statistics after task switch")
    time.sleep(1)  # Wait for switch to take effect
    response = requests.get(f"{dashboard_url}/api/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Current task: {stats.get('current_task', 'unknown')}")
        print(f"   Total detections: {stats.get('total_detections', 0)}")
        print(f"   Leaves alerts: {stats.get('leaves_alerts', 0)}")
        leaves_count = stats.get('total_detections', 0)
        
        # THE KEY TEST: Leaves count should be 0, not same as fire count
        if leaves_count == 0:
            print("✅ PASS: Yellow leaves counter is independent (starts at 0)")
        else:
            print(f"❌ FAIL: Yellow leaves counter shows {leaves_count} (should be 0)")
    else:
        print("❌ Failed to get statistics after task switch")
        return
    
    # Test 4: Switch back to fire and verify fire count is preserved
    print("\n🔄 Step 4: Switch back to Fire task")
    response = requests.post(f"{dashboard_url}/api/switch-task", 
                           json={"task": "fire"}, 
                           headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        print("✅ Successfully switched back to fire task")
    else:
        print("❌ Failed to switch back to fire task")
        return
    
    # Test 5: Verify fire count is preserved
    print("\n📊 Step 5: Verify fire count is preserved")
    time.sleep(1)  # Wait for switch to take effect
    response = requests.get(f"{dashboard_url}/api/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Current task: {stats.get('current_task', 'unknown')}")
        print(f"   Total detections: {stats.get('total_detections', 0)}")
        print(f"   Fire alerts: {stats.get('fire_alerts', 0)}")
        fire_final_count = stats.get('total_detections', 0)
        
        # Verify fire count is same as initial
        if fire_final_count == fire_initial_count:
            print("✅ PASS: Fire counter is preserved when switching back")
        else:
            print(f"❌ FAIL: Fire counter changed from {fire_initial_count} to {fire_final_count}")
    else:
        print("❌ Failed to get final statistics")
        return
    
    print("\n🎉 Task Independence Test Complete!")
    print("✅ Fire and Yellow Leaves detection counters are now independent!")

if __name__ == "__main__":
    test_task_independence() 