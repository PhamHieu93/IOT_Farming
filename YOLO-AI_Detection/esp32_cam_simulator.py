#!/usr/bin/env python3
"""
ESP32-CAM Fire Detection Simulator
Simulates ESP32-CAM behavior for fire detection system testing
"""

import cv2
import base64
import json
import time
import threading
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
import random
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ESP32CAMSimulator:
    """ESP32-CAM Fire Detection Simulator"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ESP32-CAM simulator
        
        Args:
            config: Configuration dictionary with camera and server settings
        """
        self.config = config
        self.device_id = config.get("device_id", "ESP32_CAM_SIM_001")
        self.ai_server_url = config.get("ai_server_url", "http://localhost:5001")
        self.dashboard_url = config.get("dashboard_url", "http://localhost:8080")
        self.frame_rate = config.get("frame_rate", 1)
        self.use_laptop_camera = config.get("use_laptop_camera", False)
        self.test_images_path = config.get("test_images_path", "../test/images")
        
        # Task management
        self.current_task = "fire"  # Default task
        self.task_models = {
            "fire": "fire_detection_final",
            "leaves": "yellow-leaves-best"
        }
        
        # Fire detection state
        self.fire_on = 0  # Initially 0, set to 1 when fire detected
        self.last_detection_time = None
        self.detection_history: List[Dict] = []
        
        # Request tracking for AI server health
        self.request_count = 0
        self.consecutive_failures = 0
        self.last_successful_request = datetime.now()
        
        # Camera capture
        self.camera = None
        self.is_running = False
        self.capture_thread = None
        
        # Test images list (for simulation without laptop camera)
        self.test_images = []
        self._load_test_images()
        
        logger.info(f"ESP32-CAM Simulator initialized for device: {self.device_id}")
        logger.info(f"Frame rate: {self.frame_rate} FPS")
        logger.info(f"Using laptop camera: {self.use_laptop_camera}")

    def _load_test_images(self) -> None:
        """Load test images for simulation"""
        test_path = Path(self.test_images_path)
        if test_path.exists():
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            self.test_images = [
                str(img_path) for img_path in test_path.iterdir()
                if img_path.suffix.lower() in image_extensions
            ]
            logger.info(f"Loaded {len(self.test_images)} test images from {test_path}")
        else:
            logger.warning(f"Test images path not found: {test_path}")

    def _initialize_camera(self) -> bool:
        """Initialize laptop camera if enabled"""
        if not self.use_laptop_camera:
            return True
            
        try:
            # Try different camera indices - prioritize index 2 (MacBook built-in camera)
            camera_indices = [2, 1, 0]  # Start with 2 since that's the MacBook camera
            
            for index in camera_indices:
                logger.info(f"Trying camera index {index}...")
                self.camera = cv2.VideoCapture(index)
                
                if self.camera.isOpened():
                    # Test if we can actually capture frames
                    ret, test_frame = self.camera.read()
                    if ret:
                        logger.info(f"✅ Camera {index} is working!")
                        
                        # Set camera properties
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.camera.set(cv2.CAP_PROP_FPS, 30)
                        
                        # Log actual properties
                        actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                        actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
                        logger.info(f"Camera properties: {actual_width}x{actual_height} @ {actual_fps}fps")
                        
                        return True
                    else:
                        logger.warning(f"Camera {index} opened but cannot capture frames")
                        self.camera.release()
                        self.camera = None
                else:
                    logger.warning(f"Camera {index} failed to open")
                    if self.camera:
                        self.camera.release()
                        self.camera = None
            
            logger.error("No working cameras found")
            return False
            
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False

    def _capture_frame(self) -> Optional[str]:
        """Capture a frame and return as base64 encoded string
        
        Returns:
            str: Base64 encoded image or None if capture failed
        """
        try:
            if self.use_laptop_camera and self.camera:
                # Capture from laptop camera
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to capture frame from camera")
                    return None
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame)
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                logger.info("📸 Captured frame from laptop camera")
                
            else:
                # Use random test image
                if not self.test_images:
                    logger.error("No test images available for simulation")
                    return None
                
                image_path = random.choice(self.test_images)
                image_filename = os.path.basename(image_path)
                
                # Enhanced logging for test images mode
                print(f"\n🎲 **RANDOMLY SELECTED IMAGE:**")
                print(f"   📁 File: {image_filename}")
                print(f"   🎯 Selected from {len(self.test_images)} available test images")
                
                # Read and encode image
                with open(image_path, 'rb') as img_file:
                    image_data = img_file.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def get_current_task_from_dashboard(self) -> str:
        """Get current task from dashboard"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/current-task", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return data.get("task", "fire")
        except Exception as e:
            logger.warning(f"Failed to get current task from dashboard: {e}")
        return "fire"  # Default fallback

    def _send_to_ai_server(self, image_base64: str) -> Optional[Dict]:
        """Send image to AI server for fire detection
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dict: Detection result or None if failed
        """
        try:
            # Get current task from dashboard
            self.current_task = self.get_current_task_from_dashboard()
            model_name = self.task_models.get(self.current_task, "fire_detect_final")
            
            request_data = {
                "image": image_base64,
                "model": model_name,
                "threshold": 0.5,  # Lowered from 0.5 for better camera detection
                "device_id": self.device_id
            }
            
            # Increment request counter
            self.request_count += 1
            
            # Check if we're approaching the problematic request count (~230-250)
            if self.request_count >= 200 and self.request_count % 20 == 0:
                logger.warning(f"🔄 High request count: {self.request_count} - AI server may need restart soon")
            
            # Shorter timeout for faster failure detection
            response = requests.post(
                f"{self.ai_server_url}/api/detect",
                json=request_data,
                timeout=15  # Reduced from 30 to detect failures faster
            )
            
            if response.status_code == 200:
                self.consecutive_failures = 0
                self.last_successful_request = datetime.now()
                return response.json()
            else:
                logger.error(f"AI server error: {response.status_code} - {response.text}")
                self.consecutive_failures += 1
                return None
                
        except Exception as e:
            self.consecutive_failures += 1
            if "timeout" in str(e).lower():
                logger.error(f"⏰ AI server timeout after 15s: {e} (Request #{self.request_count})")
                
                # If we've had many timeouts near the problematic range, suggest restart
                if self.request_count > 200 and self.consecutive_failures >= 2:
                    logger.error(f"🚨 AI SERVER CRITICAL: Multiple timeouts at request #{self.request_count}")
                    logger.error(f"    This is likely due to memory leak in AI server")
                    logger.error(f"    RECOMMENDATION: Restart the complete system")
                    
                    # Wait longer before next attempt when server is clearly failing
                    time.sleep(5)
                    
            else:
                logger.error(f"Failed to send to AI server: {e} (Request #{self.request_count})")
            
            # Check if we need to suggest AI server restart
            if self.consecutive_failures >= 3:
                time_since_success = (datetime.now() - self.last_successful_request).seconds
                logger.error(f"🚨 AI server health critical: {self.consecutive_failures} consecutive failures, "
                           f"{time_since_success}s since last success. Request count: {self.request_count}")
                
                # If failures persist, implement longer delays
                if self.consecutive_failures >= 5:
                    logger.error(f"🛑 AI server appears completely unresponsive - implementing longer delays")
                    time.sleep(10)  # Wait 10 seconds before next attempt
                
            return None

    def _process_detection_result(self, result: Dict) -> bool:
        """Process detection result and update detection status
        
        Args:
            result: Detection result from AI server
            
        Returns:
            bool: True if target detected, False otherwise
        """
        try:
            target_detected = False
            max_confidence = 0.0
            target_detections = []
            
            if result.get("detections"):
                for detection in result["detections"]:
                    confidence = detection.get("confidence", 0.0)
                    class_id = detection.get("class_id")
                    class_name = detection.get("class", "").lower()
                    
                    # Check detection based on current task and model-specific class mappings
                    if self.current_task == "fire":
                        # Fire model: class_id 0 = 'fire custom model_2 - v7 2024-05-21 5-56am'
                        # This model only has 1 class (fire), so class_id 0 means fire detected
                        if (class_id == 0 or 
                            "fire" in class_name):
                            target_detected = True
                            if confidence > max_confidence:
                                max_confidence = confidence
                            target_detections.append(detection)
                    elif self.current_task == "leaves":
                        # Yellow leaves model: class_id 0 = 'Yellow', class_id 1 = 'Non-Yellow'
                        # We want to detect when class_id 0 (Yellow) is found
                        if (class_id == 0 or 
                            "yellow" in class_name):
                            target_detected = True
                            if confidence > max_confidence:
                                max_confidence = confidence
                            target_detections.append(detection)
            
            # Update detection status
            previous_fire_on = self.fire_on
            if target_detected:
                self.fire_on = 1
                self.last_detection_time = datetime.now()
                
                if self.current_task == "fire":
                    logger.warning(f"🔥 FIRE DETECTED! Confidence: {max_confidence:.2f}")
                else:
                    logger.warning(f"🍃 YELLOW LEAVES DETECTED! Confidence: {max_confidence:.2f}")
            else:
                # Keep fire_on = 1 for a short period after detection stops
                if (self.last_detection_time and 
                    (datetime.now() - self.last_detection_time).seconds > 30):
                    self.fire_on = 0
            
            # Log status change
            if previous_fire_on != self.fire_on:
                if self.current_task == "fire":
                    status = "FIRE ALARM ON" if self.fire_on == 1 else "FIRE ALARM OFF"
                else:
                    status = "YELLOW LEAVES ALERT ON" if self.fire_on == 1 else "YELLOW LEAVES ALERT OFF"
                logger.info(f"🚨 Detection status changed: {status}")
            
            # Store detection in history
            detection_record = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "task": self.current_task,
                "fire_detected": target_detected,  # Keep for compatibility
                "target_detected": target_detected,
                "fire_on": self.fire_on,
                "confidence": max_confidence,
                "detections": target_detections,
                "total_detections": len(result.get("detections", [])),
                "processing_time_ms": result.get("processing_time", 0)
            }
            
            self.detection_history.append(detection_record)
            
            # Keep only last 100 detections
            if len(self.detection_history) > 100:
                self.detection_history = self.detection_history[-100:]
            
            return target_detected
            
        except Exception as e:
            logger.error(f"Failed to process detection result: {e}")
            return False

    def _send_notification_to_dashboard(self, detection_record: Dict) -> None:
        """Send fire detection notification to dashboard
        
        Args:
            detection_record: Detection result to send
        """
        try:
            # Send to dashboard API
            dashboard_data = {
                "device_id": self.device_id,
                "fire_on": self.fire_on,
                "detection_data": detection_record,
                "alert_level": "CRITICAL" if detection_record["fire_detected"] else "NONE"
            }
            
            response = requests.post(
                f"{self.dashboard_url}/api/esp32-notification",
                json=dashboard_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ Notification sent to dashboard")
            else:
                logger.warning(f"Dashboard notification failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to send dashboard notification: {e}")

    def _capture_loop(self) -> None:
        """Main capture and detection loop"""
        frame_interval = 1.0 / self.frame_rate  # Time between frames
        
        logger.info(f"🎥 Starting capture loop at {self.frame_rate} FPS")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Capture frame
                image_base64 = self._capture_frame()
                if image_base64:
                    # Send to AI server for detection
                    result = self._send_to_ai_server(image_base64)
                    if result:
                        # Process detection result
                        target_detected = self._process_detection_result(result)
                        
                        # Enhanced logging for test images mode
                        if not self.use_laptop_camera:
                            self._log_detailed_detection_results(result, target_detected)
                        
                        # Send notification to dashboard for every detection
                        if self.detection_history:
                            self._send_notification_to_dashboard(self.detection_history[-1])
                        
                        # Log current status
                        logger.info(f"📷 Frame processed - Target: {'🔥 YES' if target_detected else '❄️ NO'} | "
                                  f"Status: fire_on={self.fire_on} | "
                                  f"Detections: {len(result.get('detections', []))} | "
                                  f"Request #{self.request_count}")
                    else:
                        logger.error(f"Failed to get detection result - AI server may be slow or unresponsive "
                                   f"(Request #{self.request_count}, {self.consecutive_failures} consecutive failures)")
                        # Continue processing even if AI server fails
                        time.sleep(2)  # Brief pause before next attempt
                else:
                    logger.error("Failed to capture frame")
                
                # Wait for next frame
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                time.sleep(1)

    def _log_detailed_detection_results(self, result: Dict, target_detected: bool) -> None:
        """Log detailed detection results for test images mode"""
        try:
            print(f"\n✅ **AI DETECTION RESULTS**")
            print(f"   🎯 Current Task: {self.current_task.upper()}")
            print(f"   🤖 Model Used: {self.task_models.get(self.current_task, 'unknown')}")
            print(f"   ⏱️  Processing time: {result.get('processing_time_ms', 0):.2f}ms")
            print(f"   📏 Image processed: {result.get('image_size', {}).get('width', 'unknown')}x{result.get('image_size', {}).get('height', 'unknown')}")
            print(f"   🔍 Total detections: {result.get('detection_count', 0)}")
            
            if result.get("detections"):
                print(f"\n🔥 **AI DETECTIONS FOUND:**")
                for i, detection in enumerate(result["detections"], 1):
                    class_name = detection.get("class", "unknown")
                    class_id = detection.get("class_id", "unknown")
                    confidence = detection.get("confidence", 0)
                    
                    # Task-specific interpretation
                    if self.current_task == "fire":
                        # Fire model: only has 1 class (fire)
                        if class_id == 0:
                            display_class = "🔥 FIRE DETECTED"
                            confidence_level = "🚨 VERY HIGH" if confidence > 0.8 else "🔴 HIGH" if confidence > 0.5 else "🟡 MEDIUM"
                            is_target = True
                        else:
                            display_class = f"❓ UNKNOWN CLASS (ID: {class_id})"
                            confidence_level = "❓ UNKNOWN"
                            is_target = False
                    elif self.current_task == "leaves":
                        # Yellow leaves model: 0 = Yellow, 1 = Non-Yellow
                        if class_id == 0:
                            display_class = "🍃 YELLOW LEAVES DETECTED"
                            confidence_level = "🚨 VERY HIGH" if confidence > 0.8 else "🟡 HIGH" if confidence > 0.5 else "🟢 MEDIUM"
                            is_target = True
                        elif class_id == 1:
                            display_class = "🌿 NON-YELLOW LEAVES"
                            confidence_level = "🟢 NORMAL"
                            is_target = False
                        else:
                            display_class = f"❓ UNKNOWN CLASS (ID: {class_id})"
                            confidence_level = "❓ UNKNOWN"
                            is_target = False
                    else:
                        display_class = f"❓ UNKNOWN TASK: {self.current_task}"
                        confidence_level = "❓ UNKNOWN"
                        is_target = False
                    
                    print(f"   Detection {i}: {display_class}")
                    print(f"      Raw Class: '{class_name}' (ID: {class_id})")
                    print(f"      Confidence: {confidence:.3f} ({confidence*100:.1f}%) - {confidence_level}")
                    print(f"      Target for {self.current_task}: {'✅ YES' if is_target else '❌ NO'}")
                    
                    # Extract bounding box info
                    bbox = detection.get("bbox", {})
                    if bbox:
                        x1, y1, x2, y2 = bbox.get("x1", 0), bbox.get("y1", 0), bbox.get("x2", 0), bbox.get("y2", 0)
                        width = x2 - x1
                        height = y2 - y1
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        print(f"      📍 Bounding Box: ({x1}, {y1}) to ({x2}, {y2})")
                        print(f"      📐 Size: {width}×{height} pixels")
                        print(f"      🎯 Center: ({center_x}, {center_y})")
            else:
                print(f"   ❄️ No detections found in this frame")
            
            # Overall result with task context
            task_emoji = "🔥" if self.current_task == "fire" else "🍃"
            task_name = "FIRE" if self.current_task == "fire" else "YELLOW LEAVES"
            print(f"   {task_emoji} Overall Result: {task_name} {'DETECTED!' if target_detected else 'NOT DETECTED'}")
            print("-" * 60)
            
        except Exception as e:
            logger.error(f"Error logging detailed results: {e}")

    def start(self) -> bool:
        """Start the ESP32-CAM simulator
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Initialize camera if needed
            if not self._initialize_camera():
                if self.use_laptop_camera:
                    logger.error("Cannot start without laptop camera")
                    return False
                else:
                    logger.info("Using test images for simulation")
            
            # Check if we have images to work with
            if not self.use_laptop_camera and not self.test_images:
                logger.error("No test images available for simulation")
                return False
            
            # Start capture thread
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("🚀 ESP32-CAM Simulator started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start simulator: {e}")
            return False

    def stop(self) -> None:
        """Stop the ESP32-CAM simulator"""
        try:
            logger.info("🛑 Stopping ESP32-CAM Simulator...")
            
            self.is_running = False
            
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=5)
            
            if self.camera:
                self.camera.release()
            
            logger.info("✅ ESP32-CAM Simulator stopped")
            
        except Exception as e:
            logger.error(f"Error stopping simulator: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current simulator status
        
        Returns:
            Dict: Current status information
        """
        time_since_success = (datetime.now() - self.last_successful_request).seconds if self.last_successful_request else 0
        
        return {
            "device_id": self.device_id,
            "is_running": self.is_running,
            "fire_on": self.fire_on,
            "last_detection_time": self.last_detection_time.isoformat() if self.last_detection_time else None,
            "frame_rate": self.frame_rate,
            "use_laptop_camera": self.use_laptop_camera,
            "total_detections": len(self.detection_history),
            "camera_status": "connected" if (self.camera and self.camera.isOpened()) else "disconnected",
            "test_images_count": len(self.test_images),
            # Health monitoring
            "request_count": self.request_count,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success_sec": time_since_success,
            "ai_server_health": "critical" if self.consecutive_failures >= 3 else "warning" if self.consecutive_failures >= 1 else "good"
        }

def main():
    """Main function to run ESP32-CAM simulator"""
    print("🔥 ESP32-CAM Fire Detection Simulator")
    print("=" * 50)
    
    # Configuration
    config = {
        "device_id": "ESP32_CAM_SIM_001",
        "ai_server_url": "http://localhost:5001",
        "dashboard_url": "http://localhost:8080",
        "frame_rate": 1,  # 1 FPS (reduced from 2 FPS)
        "use_laptop_camera": False,  # Set to True to use laptop camera instead of test images
        "test_images_path": "../test/images"  # Updated to correct path
    }
    
    # Check for environment variable (for automated startup)
    use_laptop_camera = os.environ.get("ESP32_USE_LAPTOP_CAMERA", "").lower() == "true"
    
    if use_laptop_camera:
        config["use_laptop_camera"] = True
        print("📹 Using laptop camera (from environment)")
    elif "ESP32_USE_LAPTOP_CAMERA" in os.environ:
        print("🖼️ Using test images for simulation (from environment)")
    else:
        # Ask user for camera preference (interactive mode)
        try:
            camera_choice = input("Use laptop camera? (y/n, default=n): ").strip().lower()
            if camera_choice in ['y', 'yes']:
                config["use_laptop_camera"] = True
                print("📹 Will use laptop camera")
            else:
                print("🖼️ Will use test images for simulation")
        except:
            print("🖼️ Using test images for simulation (default)")
    
    # Create and start simulator
    simulator = ESP32CAMSimulator(config)
    
    try:
        if simulator.start():
            print(f"\n✅ Simulator running with device ID: {config['device_id']}")
            print(f"📊 Dashboard URL: {config['dashboard_url']}")
            print(f"🤖 AI Server URL: {config['ai_server_url']}")
            print(f"🎥 Frame Rate: {config['frame_rate']} FPS")
            print(f"📷 Camera Mode: {'Laptop Camera' if config['use_laptop_camera'] else 'Test Images'}")
            print("\nPress Ctrl+C to stop...")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
        else:
            print("❌ Failed to start simulator")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down simulator...")
        simulator.stop()
        print("👋 Goodbye!")
    except Exception as e:
        logger.error(f"Simulator error: {e}")
        simulator.stop()

if __name__ == "__main__":
    main() 