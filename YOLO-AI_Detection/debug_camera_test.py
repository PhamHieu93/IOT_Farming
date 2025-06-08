#!/usr/bin/env python3
"""
Debug script to test camera capture with AI server
"""
import cv2
import base64
import requests
import json

def test_camera_capture():
    """Test live camera capture with AI server"""
    print("🔍 Testing camera capture with fire detection...")
    
    # Use same camera index as ESP32 simulator (camera 1 - MacBook camera)
    cap = cv2.VideoCapture(1)
    
    if not cap.isOpened():
        print("❌ Cannot open camera index 1")
        return
    
    # Set same properties as ESP32 simulator
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("📸 Capturing frame...")
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Failed to capture frame")
        cap.release()
        return
    
    # Save frame for inspection
    cv2.imwrite('debug_camera_frame.jpg', frame)
    print("💾 Frame saved as: debug_camera_frame.jpg")
    
    # Convert to base64 (same as ESP32 simulator)
    _, buffer = cv2.imencode('.jpg', frame)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    
    # Test multiple confidence thresholds to see if there are weak detections
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    for threshold in thresholds:
        print(f"\n🎯 **TESTING THRESHOLD: {threshold}**")
        
        data = {
            'image': image_base64,
            'model': 'fire_detection_final',
            'threshold': threshold,
            'device_id': f'DEBUG_T{threshold}'
        }
        
        try:
            response = requests.post('http://localhost:5001/api/detect', json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"   ⏱️  Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   🔍 Total detections: {len(result.get('detections', []))}")
                
                if result.get('detections'):
                    print(f"   🔥 **DETECTIONS FOUND:**")
                    for i, det in enumerate(result.get('detections', []), 1):
                        class_name = det.get('class', 'unknown')
                        confidence = det.get('confidence', 0)
                        
                        # Check if it's fire detection
                        is_fire = (class_name == '0' or class_name == 0 or 
                                  str(class_name).lower() == 'fire')
                        
                        status = "🔥 FIRE" if is_fire else "❄️ NO_FIRE"
                        confidence_pct = confidence * 100
                        
                        print(f"      {status}: {confidence:.3f} ({confidence_pct:.1f}%)")
                else:
                    print(f"   ❄️ No detections")
                    
            else:
                print(f"   ❌ AI server error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    cap.release()
    print(f"\n📁 Check 'debug_camera_frame.jpg' to see what the camera captured")

if __name__ == "__main__":
    test_camera_capture() 