#!/usr/bin/env python3
"""
Debug script to test fire detection and see exact AI server response
"""

import base64
import json
import requests
from PIL import Image
import sys

def test_detection():
    """Test detection with a fire image"""
    
    try:
        image_path = input("Enter path to your fire image: ").strip()
        if not image_path:
            print("No image path provided. Exiting.")
            return
            
        print(f"📸 Loading image: {image_path}")
        
        # Load and encode image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        print("✅ Image loaded and encoded")
        
        # Test with different confidence thresholds
        thresholds = [0.1, 0.15, 0.3, 0.5]
        
        for threshold in thresholds:
            print(f"\n🎯 **TESTING THRESHOLD: {threshold}**")
            
            # Send to AI server
            request_data = {
                "image": image_data,
                "model": "fire_detection_final",
                "threshold": threshold,
                "device_id": "DEBUG_TEST"
            }
            
            try:
                response = requests.post(
                    "http://localhost:5001/api/detect",
                    json=request_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print(f"   ✅ AI Server Response:")
                    print(f"   📊 Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                    print(f"   🔧 Model used: {result.get('model_used')}")
                    print(f"   🎚️  Threshold: {result.get('confidence_threshold')}")
                    print(f"   📏 Image size: {result.get('image_size')}")
                    print(f"   🔍 Total detections: {len(result.get('detections', []))}")
                    
                    if result.get('detections'):
                        print(f"   🔥 **DETECTIONS FOUND:**")
                        for i, detection in enumerate(result.get('detections', []), 1):
                            class_id = detection.get('class_id')
                            class_name = detection.get('class', 'unknown')
                            confidence = detection.get('confidence', 0)
                            bbox = detection.get('bbox', {})
                            
                            print(f"      Detection {i}:")
                            print(f"        🏷️  Class ID: {class_id}")
                            print(f"        📝 Class Name: '{class_name}'")
                            print(f"        🎯 Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
                            print(f"        📦 BBox: {bbox}")
                            
                            # Check if this would be considered fire
                            is_fire = (class_id == 0 or "fire" in str(class_name).lower())
                            print(f"        🔥 Is Fire: {is_fire}")
                    else:
                        print(f"   ❄️ No detections found")
                        
                    # Test dashboard logic
                    print(f"\n   🧠 **DASHBOARD LOGIC TEST:**")
                    target_detected = False
                    max_confidence = 0.0
                    
                    if result.get("detections"):
                        for detection in result["detections"]:
                            class_id = detection.get("class_id")
                            class_name = detection.get("class", "").lower()
                            confidence = detection.get("confidence", 0.0)
                            
                            print(f"      Checking: class_id={class_id}, class_name='{class_name}', confidence={confidence}")
                            
                            # Fire detection logic (same as dashboard)
                            is_target = False
                            if class_id == 0 or "fire" in class_name:
                                is_target = True
                                
                            print(f"      Is fire target: {is_target}")
                            
                            if is_target and confidence > max_confidence:
                                target_detected = True
                                max_confidence = confidence
                    
                    print(f"   🎯 Final result: target_detected={target_detected}, max_confidence={max_confidence:.3f}")
                    
                else:
                    print(f"   ❌ AI server error: {response.status_code}")
                    print(f"   📝 Response: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
        
    except FileNotFoundError:
        print(f"❌ Image file not found: {image_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔍 Fire Detection Debug Test")
    print("=" * 50)
    test_detection() 