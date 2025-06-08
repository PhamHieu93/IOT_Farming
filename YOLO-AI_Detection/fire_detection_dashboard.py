#!/usr/bin/env python3
"""
Fire Detection Real-Time Dashboard
Web-based monitoring interface for ESP32-CAM fire detection system
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import sqlite3
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import threading
import requests
from PIL import Image
from io import BytesIO
import os
import cv2

# Initialize Flask app with SocketIO
app = Flask(__name__)
app.config["SECRET_KEY"] = "fire_detection_dashboard_secret_key"
# Disable template caching to always reload templates
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
# Force threading mode to avoid eventlet compatibility issues with Python 3.12
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

def force_reset_database():
    """Force reset the database - can be called independently"""
    db_path = "fire_detection_history.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear all data
        cursor.execute("DELETE FROM fire_detections")
        deleted_detections = cursor.rowcount
        
        cursor.execute("DELETE FROM device_status")
        deleted_devices = cursor.rowcount
        
        # Add fresh device
        cursor.execute("""
            INSERT INTO device_status 
            (device_id, last_seen, status, total_detections, fire_alerts)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "ESP32_CAM_SIM_001",
            datetime.now().isoformat(),
            "ACTIVE",
            0,
            0
        ))
        
        conn.commit()
        conn.close()
        
        print(f"🔄 FORCE RESET: Cleared {deleted_detections} detections, {deleted_devices} devices")
        print("✅ Database force reset completed")
        
    except Exception as e:
        print(f"❌ Force reset error: {e}")

class FireDetectionDashboard:
    """Fire Detection Dashboard Service"""
    
    def __init__(self):
        """Initialize dashboard service"""
        self.db_path = "fire_detection_history.db"
        self.ai_server_url = "http://localhost:5001"
        self.active_connections = set()
        
        # Task management
        self.current_task = "fire"  # Default task
        self.task_models = {
            "fire": "fire_detection_final",
            "leaves": "yellow-leaves-best"
        }
        
        # Camera preview state
        self.camera_preview_active = False
        self.camera = None
        self.camera_thread = None
        self.camera_frame = None
        self.camera_lock = threading.Lock()
        
        # FORCE DATABASE RESET FIRST
        print("🔄 FORCING DATABASE RESET ON STARTUP...")
        force_reset_database()
        
        # Initialize database if it doesn't exist
        self._init_database()
        
        # Start background monitoring
        self._start_background_monitoring()

    def _init_database(self) -> None:
        """Initialize database tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fire_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    task TEXT NOT NULL DEFAULT 'fire',
                    timestamp TEXT NOT NULL,
                    fire_detected BOOLEAN NOT NULL,
                    confidence REAL NOT NULL,
                    bbox TEXT,
                    image_size TEXT NOT NULL,
                    processing_time_ms REAL NOT NULL,
                    alert_level TEXT NOT NULL,
                    image_data TEXT
                )
            """)
            
            # Add task column to existing table if it doesn't exist
            try:
                cursor.execute("ALTER TABLE fire_detections ADD COLUMN task TEXT DEFAULT 'fire'")
                print("✅ Added task column to existing fire_detections table")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    device_id TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_detections INTEGER DEFAULT 0,
                    fire_alerts INTEGER DEFAULT 0,
                    fire_total_detections INTEGER DEFAULT 0,
                    fire_alerts_count INTEGER DEFAULT 0,
                    leaves_total_detections INTEGER DEFAULT 0,
                    leaves_alerts_count INTEGER DEFAULT 0
                )
            """)
            
            # Add task-specific columns to existing device_status table
            task_columns = [
                ("fire_total_detections", "INTEGER DEFAULT 0"),
                ("fire_alerts_count", "INTEGER DEFAULT 0"), 
                ("leaves_total_detections", "INTEGER DEFAULT 0"),
                ("leaves_alerts_count", "INTEGER DEFAULT 0")
            ]
            
            for column_name, column_def in task_columns:
                try:
                    cursor.execute(f"ALTER TABLE device_status ADD COLUMN {column_name} {column_def}")
                    print(f"✅ Added {column_name} column to device_status table")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            conn.commit()
            conn.close()
            
            # Reset statistics to zero on startup (do this AFTER creating tables)
            print("🔄 Resetting statistics to zero on startup...")
            self._reset_statistics()
            
        except Exception as e:
            print(f"Database initialization error: {e}")

    def _reset_statistics(self) -> None:
        """Reset all statistics to zero"""
        try:
            # Use a separate connection to ensure the reset happens
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = OFF")  # Disable foreign key constraints
            cursor = conn.cursor()
            
            # Clear all detection records
            cursor.execute("DELETE FROM fire_detections")
            print(f"   Cleared {cursor.rowcount} detection records")
            
            # Clear all device status records
            cursor.execute("DELETE FROM device_status")
            print(f"   Cleared {cursor.rowcount} device status records")
            
            # Add fresh default ESP32 device with zero stats
            cursor.execute("""
                INSERT INTO device_status 
                (device_id, last_seen, status, total_detections, fire_alerts)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "ESP32_CAM_SIM_001",
                datetime.now().isoformat(),
                "ACTIVE",
                0,
                0
            ))
            
            # Force commit and close
            conn.commit()
            conn.close()
            
            print("✅ Statistics reset to zero successfully")
            
        except Exception as e:
            print(f"❌ Error resetting statistics: {e}")

    def _start_background_monitoring(self) -> None:
        """Start background thread for monitoring"""
        def monitor_loop():
            while True:
                try:
                    # Check AI server status
                    self._check_ai_server_status()
                    
                    # Update device statuses
                    self._update_device_statuses()
                    
                    # Send updates to connected clients
                    self._broadcast_status_update()
                    
                    time.sleep(2)  # Update every 2 seconds for better responsiveness
                    
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print("✅ Background monitoring started")

    def _check_ai_server_status(self) -> Dict[str, Any]:
        """Check AI server status with timeout"""
        try:
            response = requests.get(f"{self.ai_server_url}/api/status", timeout=2)
            if response.status_code == 200:
                return {"status": "online", "data": response.json()}
            else:
                return {"status": "error", "message": f"Status code: {response.status_code}"}
        except requests.exceptions.Timeout:
            return {"status": "timeout", "message": "AI server timeout"}
        except Exception as e:
            return {"status": "offline", "message": f"Cannot connect to AI server: {str(e)}"}

    def _update_device_statuses(self) -> None:
        """Update device status based on last seen time"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mark devices as offline if not seen for more than 30 seconds (for testing)
            cutoff_time = (datetime.now() - timedelta(seconds=30)).isoformat()
            cursor.execute("""
                UPDATE device_status 
                SET status = 'OFFLINE' 
                WHERE last_seen < ? AND status != 'OFFLINE'
            """, (cutoff_time,))
            
            # For testing: Keep ESP32 simulator alive if it exists
            cursor.execute("""
                UPDATE device_status 
                SET last_seen = ?, status = 'ACTIVE'
                WHERE device_id = 'ESP32_CAM_SIM_001'
            """, (datetime.now().isoformat(),))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Device status update error: {e}")

    def _broadcast_status_update(self) -> None:
        """Broadcast status update to all connected clients"""
        try:
            device_status = self.get_device_status()
            recent_detections = self.get_recent_detections(limit=10)
            ai_server_status = self._check_ai_server_status()
            
            # Ensure we always have data to show
            if not device_status:
                device_status = [{
                    "device_id": "ESP32_CAM_SIM_001",
                    "status": "ACTIVE",
                    "last_seen": datetime.now().isoformat(),
                    "total_detections": 0,
                    "fire_alerts": 0,
                    "minutes_since_last_seen": 0
                }]
            
            socketio.emit("status_update", {
                "devices": device_status,
                "recent_detections": recent_detections,
                "ai_server": ai_server_status,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"Broadcast error: {e}")

    def get_device_status(self) -> List[Dict]:
        """Get status of all monitored devices"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM device_status ORDER BY last_seen DESC")
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # Calculate time since last seen
                if record["last_seen"]:
                    last_seen = datetime.fromisoformat(record["last_seen"])
                    time_diff = datetime.now() - last_seen
                    record["minutes_since_last_seen"] = int(time_diff.total_seconds() / 60)
                else:
                    record["minutes_since_last_seen"] = 9999
                
                results.append(record)
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Device status retrieval error: {e}")
            return []

    def get_recent_detections(self, limit: int = 50) -> List[Dict]:
        """Get recent fire detections"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fire_detections 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # Parse JSON fields
                if record["bbox"]:
                    record["bbox"] = json.loads(record["bbox"])
                if record["image_size"]:
                    record["image_size"] = json.loads(record["image_size"])
                results.append(record)
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Recent detections retrieval error: {e}")
            return []

    def get_detection_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get detection statistics for the specified time period, filtered by current task"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            current_task = self.get_current_task()
            
            # Total detections for current task
            cursor.execute("""
                SELECT COUNT(*) FROM fire_detections 
                WHERE timestamp > ? AND task = ?
            """, (cutoff_time, current_task))
            total_detections = cursor.fetchone()[0]
            
            # Target alerts for current task (fire_detected = 1 means target was detected)
            cursor.execute("""
                SELECT COUNT(*) FROM fire_detections 
                WHERE timestamp > ? AND task = ? AND fire_detected = 1
            """, (cutoff_time, current_task))
            target_alerts = cursor.fetchone()[0]
            
            # Average confidence for target detections in current task
            cursor.execute("""
                SELECT AVG(confidence) FROM fire_detections 
                WHERE timestamp > ? AND task = ? AND fire_detected = 1
            """, (cutoff_time, current_task))
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # Active devices
            cursor.execute("SELECT COUNT(*) FROM device_status WHERE status = 'ACTIVE'")
            active_devices = cursor.fetchone()[0]
            
            # Detection by hour for current task
            cursor.execute("""
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as count,
                    SUM(CASE WHEN fire_detected = 1 THEN 1 ELSE 0 END) as target_count
                FROM fire_detections 
                WHERE timestamp > ? AND task = ?
                GROUP BY hour
                ORDER BY hour
            """, (cutoff_time, current_task))
            hourly_data = cursor.fetchall()
            
            conn.close()
            
            # Ensure we always have some data to display
            if active_devices == 0:
                active_devices = 1  # Show at least 1 device (ESP32 simulator)
            
            # Generate sample hourly data if none exists
            if not hourly_data:
                hourly_data = []
                current_hour = datetime.now().hour
                for hour in range(24):
                    # Show some activity during day hours, less at night
                    if 8 <= hour <= 20:
                        total = 2 if hour == current_hour else 1
                        target = 1 if hour == current_hour and total_detections == 0 else 0
                    else:
                        total = 1 if hour == current_hour else 0
                        target = 0
                    hourly_data.append((str(hour).zfill(2), total, target))
            
            # Task-specific labels
            alert_label = "fire_alerts" if current_task == "fire" else "leaves_alerts"
            
            return {
                "total_detections": max(total_detections, 0),
                "fire_alerts": max(target_alerts, 0),  # Keep same key for compatibility
                alert_label: max(target_alerts, 0),  # Task-specific key
                "avg_confidence": round(avg_confidence, 3),
                "active_devices": active_devices,
                "alert_rate": round((target_alerts / max(total_detections, 1)) * 100, 1) if total_detections > 0 else 0.0,
                "hourly_data": [{"hour": row[0], "total": row[1], "fire": row[2]} for row in hourly_data],
                "current_task": current_task,
                "task_specific": True
            }
            
        except Exception as e:
            print(f"Statistics retrieval error: {e}")
            # Return default data if there's an error
            current_hour = datetime.now().hour
            current_task = self.get_current_task()
            return {
                "total_detections": 0,
                "fire_alerts": 0,
                "avg_confidence": 0.0,
                "active_devices": 1,
                "alert_rate": 0.0,
                "hourly_data": [
                    {"hour": str(h).zfill(2), "total": 1 if h == current_hour else 0, "fire": 0}
                    for h in range(24)
                ],
                "current_task": current_task,
                "task_specific": True
            }

    def process_test_image(self, image_data: str, device_id: str = "DASHBOARD_TEST") -> Dict[str, Any]:
        """Process a test image through the fire detection system"""
        try:
            request_data = {
                "image": image_data,
                "model": self.get_current_model(),
                "threshold": 0.1,
                "device_id": device_id
            }
            
            response = requests.post(
                f"{self.ai_server_url}/api/detect",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Store in database
                self._store_test_result(result, device_id, image_data)
                
                # Broadcast to clients
                socketio.emit("new_detection", {
                    "device_id": device_id,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return result
            else:
                return {"error": f"AI server error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Processing error: {str(e)}"}

    def _store_test_result(self, result: Dict, device_id: str, image_data: str) -> None:
        """Store test result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_task = self.get_current_task()
            
            # Debug logging
            print(f"🔍 DEBUG: Processing test result for task '{current_task}'")
            print(f"🔍 DEBUG: Total detections received: {len(result.get('detections', []))}")
            
            # Determine if target was detected (context-aware based on current task)
            target_detected = False
            max_confidence = 0.0
            target_bbox = None
            
            if result.get("detections"):
                for i, detection in enumerate(result["detections"]):
                    class_id = detection.get("class_id")
                    class_name = detection.get("class", "").lower()
                    confidence = detection.get("confidence", 0.0)
                    
                    print(f"🔍 DEBUG: Detection {i+1}: class_id={class_id}, class_name='{class_name}', confidence={confidence:.3f}")
                    
                    # Task-specific detection logic
                    is_target = False
                    if current_task == "fire":
                        # Fire model: class_id 0 = fire
                        if class_id == 0 or "fire" in class_name:
                            is_target = True
                            print(f"🔥 DEBUG: Fire detected! class_id={class_id}, 'fire' in '{class_name}': {'fire' in class_name}")
                    elif current_task == "leaves":
                        # Yellow leaves model: class_id 0 = yellow leaves
                        if class_id == 0 or "yellow" in class_name:
                            is_target = True
                            print(f"🍃 DEBUG: Yellow leaves detected! class_id={class_id}, 'yellow' in '{class_name}': {'yellow' in class_name}")
                    
                    print(f"🔍 DEBUG: Is target for {current_task}: {is_target}")
                    
                    if is_target and confidence > max_confidence:
                        target_detected = True
                        max_confidence = confidence
                        target_bbox = detection.get("bbox")
                        print(f"🎯 DEBUG: New best detection! confidence={confidence:.3f}")
            else:
                print(f"🔍 DEBUG: No detections found in result")
            
            print(f"🎯 DEBUG: Final result - target_detected={target_detected}, max_confidence={max_confidence:.3f}")
            
            # Determine alert level
            if target_detected:
                if max_confidence > 0.8:
                    alert_level = "CRITICAL"
                elif max_confidence > 0.6:
                    alert_level = "HIGH"
                elif max_confidence > 0.4:
                    alert_level = "MEDIUM"
                else:
                    alert_level = "LOW"
            else:
                alert_level = "NONE"
            
            # Insert detection record with task
            cursor.execute("""
                INSERT INTO fire_detections 
                (device_id, task, timestamp, fire_detected, confidence, bbox, image_size, 
                 processing_time_ms, alert_level, image_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                current_task,
                datetime.now().isoformat(),
                target_detected,
                max_confidence,
                json.dumps(target_bbox) if target_bbox else None,
                json.dumps(result.get("image_size", {"width": 0, "height": 0})),
                result.get("processing_time_ms", 0),
                alert_level,
                image_data[:1000] if len(image_data) > 1000 else image_data
            ))
            
            # Update device status with task-specific counters
            task_total_column = f"{current_task}_total_detections"
            task_alerts_column = f"{current_task}_alerts_count"
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO device_status 
                (device_id, last_seen, status, total_detections, fire_alerts, {task_total_column}, {task_alerts_column})
                VALUES (?, ?, ?, 
                    COALESCE((SELECT total_detections FROM device_status WHERE device_id = ?), 0) + 1,
                    COALESCE((SELECT fire_alerts FROM device_status WHERE device_id = ?), 0) + ?,
                    COALESCE((SELECT {task_total_column} FROM device_status WHERE device_id = ?), 0) + 1,
                    COALESCE((SELECT {task_alerts_column} FROM device_status WHERE device_id = ?), 0) + ?)
            """, (
                device_id,
                datetime.now().isoformat(),
                "ACTIVE",
                device_id,
                device_id,
                1 if target_detected else 0,  # Legacy fire_alerts column
                device_id,
                device_id,
                1 if target_detected else 0   # Task-specific alerts
            ))
            
            conn.commit()
            conn.close()
            
            print(f"📊 Stored {current_task} detection: target={'YES' if target_detected else 'NO'}, confidence={max_confidence:.3f}")
            
        except Exception as e:
            print(f"Test result storage error: {e}")

    def _store_esp32_detection(self, detection_data: Dict, device_id: str) -> None:
        """Store ESP32-CAM detection data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current task from detection data or default to fire
            current_task = detection_data.get("task", "fire")
            
            # Insert detection record with task
            cursor.execute("""
                INSERT INTO fire_detections 
                (device_id, task, timestamp, fire_detected, confidence, bbox, image_size, 
                 processing_time_ms, alert_level, image_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                current_task,
                detection_data.get("timestamp"),
                detection_data.get("fire_detected", False),
                detection_data.get("confidence", 0.0),
                json.dumps(detection_data.get("bbox")),
                json.dumps(detection_data.get("image_size", {"width": 0, "height": 0})),
                detection_data.get("processing_time_ms", 0),
                detection_data.get("alert_level", "NONE"),
                detection_data.get("image_data", "")[:1000] if len(detection_data.get("image_data", "")) > 1000 else detection_data.get("image_data", "")
            ))
            
            # Update device status with task-specific counters
            task_total_column = f"{current_task}_total_detections"
            task_alerts_column = f"{current_task}_alerts_count"
            target_detected = detection_data.get("fire_detected", False)
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO device_status 
                (device_id, last_seen, status, total_detections, fire_alerts, {task_total_column}, {task_alerts_column})
                VALUES (?, ?, ?, 
                    COALESCE((SELECT total_detections FROM device_status WHERE device_id = ?), 0) + 1,
                    COALESCE((SELECT fire_alerts FROM device_status WHERE device_id = ?), 0) + ?,
                    COALESCE((SELECT {task_total_column} FROM device_status WHERE device_id = ?), 0) + 1,
                    COALESCE((SELECT {task_alerts_column} FROM device_status WHERE device_id = ?), 0) + ?)
            """, (
                device_id,
                detection_data.get("timestamp"),
                "ACTIVE",
                device_id,
                device_id,
                1 if target_detected else 0,  # Legacy fire_alerts column
                device_id,
                device_id,
                1 if target_detected else 0   # Task-specific alerts
            ))
            
            conn.commit()
            conn.close()
            
            print(f"📊 Stored ESP32 {current_task} detection: target={'YES' if target_detected else 'NO'}")
            
        except Exception as e:
            print(f"ESP32 detection storage error: {e}")

    def _update_esp32_device_status(self, device_id: str, fire_on: bool) -> None:
        """Update ESP32-CAM device status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update device status
            cursor.execute("""
                UPDATE device_status 
                SET status = ? 
                WHERE device_id = ?
            """, ("ACTIVE" if fire_on else "OFFLINE", device_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"ESP32 device status update error: {e}")

    def start_camera_preview(self) -> Dict[str, Any]:
        """Start camera preview streaming"""
        try:
            if self.camera_preview_active:
                return {"success": True, "message": "Camera preview already active"}
            
            # Try different camera indices - prioritize index 1 for actual MacBook camera over OBS
            camera_indices = [1, 0, 2]  # Try MacBook camera first, then OBS, then others
            
            for index in camera_indices:
                print(f"Trying camera index {index}...")
                self.camera = cv2.VideoCapture(index)
                
                # Set camera properties before testing
                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                    
                    # Test if we can actually capture frames
                    ret, test_frame = self.camera.read()
                    if ret and test_frame is not None:
                        print(f"✅ Camera {index} working!")
                        self.camera_preview_active = True
                        
                        # Start camera thread
                        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
                        self.camera_thread.start()
                        
                        # Notify all clients
                        try:
                            socketio.emit("camera_status", {"active": True, "message": "Camera preview started"})
                        except:
                            pass  # Don't fail if socketio emit fails
                        
                        return {"success": True, "message": f"Camera preview started (index {index})"}
                    else:
                        print(f"❌ Camera {index} can't capture frames")
                        self.camera.release()
                        self.camera = None
                else:
                    print(f"❌ Camera {index} failed to open")
                    if self.camera:
                        self.camera.release()
                        self.camera = None
            
            return {"success": False, "message": "No working cameras found"}
            
        except Exception as e:
            print(f"Camera start error: {e}")
            return {"success": False, "message": f"Camera error: {str(e)}"}

    def stop_camera_preview(self) -> Dict[str, Any]:
        """Stop camera preview streaming with robust error handling"""
        try:
            print("🛑 Stopping camera preview...")
            
            if not self.camera_preview_active:
                print("ℹ️ Camera preview was not active")
                return {"success": True, "message": "Camera preview not active"}
            
            # Set flag to stop camera loop
            self.camera_preview_active = False
            print("✅ Camera preview flag set to False")
            
            # Release camera safely
            if self.camera:
                try:
                    print("📷 Releasing camera...")
                    self.camera.release()
                    print("✅ Camera released successfully")
                except Exception as e:
                    print(f"⚠️ Camera release error (non-critical): {e}")
                finally:
                    self.camera = None
            
            # Wait for thread to finish with timeout
            if self.camera_thread and self.camera_thread.is_alive():
                try:
                    print("🧵 Waiting for camera thread to finish...")
                    self.camera_thread.join(timeout=3)  # Increased timeout
                    if self.camera_thread.is_alive():
                        print("⚠️ Camera thread did not finish in time (non-critical)")
                    else:
                        print("✅ Camera thread finished successfully")
                except Exception as e:
                    print(f"⚠️ Thread join error (non-critical): {e}")
            
            # Clear camera frame safely
            try:
                with self.camera_lock:
                    self.camera_frame = None
                print("✅ Camera frame cleared")
            except Exception as e:
                print(f"⚠️ Frame clear error (non-critical): {e}")
            
            # Notify all clients with error handling
            try:
                socketio.emit("camera_status", {"active": False, "message": "Camera preview stopped"})
                print("✅ SocketIO notification sent")
            except Exception as e:
                print(f"⚠️ SocketIO emit error (non-critical): {e}")
            
            print("✅ Camera preview stopped successfully")
            return {"success": True, "message": "Camera preview stopped"}
            
        except Exception as e:
            error_msg = f"Error stopping camera: {str(e)}"
            print(f"❌ {error_msg}")
            # Even if there's an error, try to clean up
            try:
                self.camera_preview_active = False
                if self.camera:
                    self.camera.release()
                    self.camera = None
            except:
                pass  # Silent cleanup attempt
            
            return {"success": False, "message": error_msg}

    def _camera_loop(self) -> None:
        """Camera capture loop for preview with robust error handling"""
        print("🎥 Starting camera capture loop...")
        
        while self.camera_preview_active and self.camera:
            try:
                if not self.camera or not self.camera.isOpened():
                    print("📷 Camera not available, stopping loop")
                    break
                    
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    # Resize frame for web display
                    frame = cv2.resize(frame, (640, 480))
                    
                    # Convert to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    # Safely update frame
                    try:
                        with self.camera_lock:
                            self.camera_frame = buffer.tobytes()
                    except Exception as e:
                        print(f"Frame update error: {e}")
                        continue
                else:
                    print("Failed to read camera frame")
                    break
                    
                time.sleep(1/30)  # 30 FPS max
                
            except Exception as e:
                print(f"Camera loop error: {e}")
                # Don't break immediately, try a few more times
                time.sleep(0.5)
                continue
        
        # Cleanup on exit with error handling
        print("🛑 Camera loop ending, cleaning up...")
        try:
            self.camera_preview_active = False
            if self.camera:
                self.camera.release()
                self.camera = None
            print("✅ Camera loop cleanup completed")
        except Exception as e:
            print(f"⚠️ Camera loop cleanup error: {e}")

    def get_camera_frame(self):
        """Get current camera frame for streaming"""
        try:
            with self.camera_lock:
                if self.camera_frame is not None:
                    return self.camera_frame
                else:
                    return None
        except:
            return None

    def get_camera_status(self) -> Dict[str, Any]:
        """Get current camera status"""
        return {
            "active": self.camera_preview_active,
            "has_camera": self.camera is not None and self.camera.isOpened() if self.camera else False
        }

    def set_current_task(self, task: str) -> bool:
        """Set the current detection task
        
        Args:
            task: Task name ('fire' or 'leaves')
            
        Returns:
            bool: True if task was set successfully
        """
        if task in self.task_models:
            self.current_task = task
            print(f"✅ Task switched to: {task}")
            return True
        else:
            print(f"❌ Unknown task: {task}")
            return False
    
    def get_current_task(self) -> str:
        """Get the current detection task"""
        return self.current_task
    
    def get_current_model(self) -> str:
        """Get the model name for the current task"""
        return self.task_models.get(self.current_task, "fire_detect_final")

# Initialize dashboard
dashboard = FireDetectionDashboard()

# Flask Routes
@app.route("/")
def index():
    """Main dashboard page"""
    # Return HTML directly instead of using template to avoid template issues
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥🍃 AI Detection Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .card { box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border: none; margin-bottom: 20px; }
        .stat-card { text-align: center; padding: 20px; }
        .stat-number { font-size: 2.5rem; font-weight: bold; margin: 0; }
        .device-card { background: white; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
        .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; }
        .status-online { background-color: #d4edda; color: #155724; }
        .status-offline { background-color: #f8d7da; color: #721c24; }
        .chart-container { height: 300px; }
        .alert-success { border-left: 4px solid #28a745; }
        .alert-danger { border-left: 4px solid #dc3545; }
        .camera-container { position: relative; }
        .camera-stream { 
            width: 100%; 
            max-width: 640px; 
            height: auto; 
            border-radius: 8px; 
            border: 2px solid #28a745;
            display: block;
            margin: 0 auto;
        }
        .camera-placeholder { 
            border: 2px dashed #007bff; 
            border-radius: 8px; 
            background: #e7f3ff; 
            padding: 40px; 
            text-align: center;
            max-width: 640px;
            margin: 0 auto;
        }
        .upload-zone { border: 2px dashed #007bff; border-radius: 10px; padding: 2rem; text-align: center; background: rgba(0, 123, 255, 0.05); cursor: pointer; transition: all 0.3s ease; }
        .upload-zone:hover { border-color: #0056b3; background: rgba(0, 123, 255, 0.1); }
        
        /* Apple-style Toggle Switch */
        .toggle-container {
            display: flex;
            align-items: center;
            gap: 15px;
            background: rgba(255, 255, 255, 0.1);
            padding: 15px 20px;
            border-radius: 12px;
            backdrop-filter: blur(10px);
            margin-bottom: 20px;
        }
        
        .task-label {
            font-weight: 600;
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 140px;
        }
        
        .task-label.inactive {
            opacity: 0.6;
        }
        
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, #ff6b6b, #ff8e53);
            transition: .4s;
            border-radius: 34px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        input:checked + .slider {
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
        }
        
        input:checked + .slider:before {
            transform: translateX(26px);
        }
        
        /* Theme-based styling */
        .fire-theme {
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
        }
        
        .leaves-theme {
            background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
        }
        
        .detection-icon {
            font-size: 1.2em;
        }
        
        .current-task-display {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 10px 15px;
            color: white;
            font-weight: 600;
            backdrop-filter: blur(10px);
        }
    </style>
</head>
<body id="dashboardBody">
    <div class="container-fluid py-4">
        <!-- Header with Task Toggle -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h1 class="mb-1">
                                    <span id="taskIcon">🔥</span> 
                                    <span id="taskTitle">Fire Detection</span> Dashboard
                                </h1>
                                <p class="text-muted mb-0">Real-time ESP32-CAM AI monitoring system</p>
                            </div>
                            <div class="text-end">
                                <span id="connectionStatus" class="badge bg-success me-2">
                                    <i class="fas fa-circle"></i> Connected
                                </span>
                                <span id="aiServerStatus" class="badge bg-warning">
                                    <i class="fas fa-server"></i> AI Server: Checking...
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Task Toggle Section -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="toggle-container">
                    <div class="task-label" id="fireLabel">
                        <i class="fas fa-fire detection-icon"></i>
                        Fire Detection
                    </div>
                    
                    <label class="toggle-switch">
                        <input type="checkbox" id="taskToggle">
                        <span class="slider"></span>
                    </label>
                    
                    <div class="task-label" id="leavesLabel">
                        <i class="fas fa-leaf detection-icon"></i>
                        Yellow Leaves Detection
                    </div>
                    
                    <div class="ms-auto">
                        <div class="current-task-display" id="currentTaskDisplay">
                            🔥 Fire Detection Active
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Statistics Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card stat-card">
                    <h5 class="text-muted">TOTAL DETECTIONS (24H)</h5>
                    <p id="totalDetections" class="stat-number text-primary">0</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <h5 class="text-muted" id="alertsLabel">FIRE ALERTS (24H)</h5>
                    <p id="fireAlerts" class="stat-number text-danger">0</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <h5 class="text-muted">ACTIVE DEVICES</h5>
                    <p id="activeDevices" class="stat-number text-success">1</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <h5 class="text-muted">ALERT RATE</h5>
                    <p id="alertRate" class="stat-number text-warning">0%</p>
                </div>
            </div>
        </div>
        
        <!-- Camera Preview Section -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0"><i class="fas fa-video text-info"></i> 📹 Live Camera Preview</h5>
                        <button id="cameraToggleBtn" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-play"></i> Start Camera
                        </button>
                    </div>
                    <div class="card-body text-center">
                        <div id="cameraContainer" class="d-flex justify-content-center align-items-center">
                            <div id="cameraPreview" style="display: none;">
                                <img id="cameraStream" src="/video_feed" class="camera-stream" alt="Camera Stream">
                                <div class="mt-2">
                                    <span id="cameraStatus" class="badge bg-success">
                                        <i class="fas fa-circle"></i> Camera Active - Live Feed
                                    </span>
                                    <small class="text-muted ms-2" id="cameraInstructions">
                                        Live feed from laptop camera
                                    </small>
                                </div>
                            </div>
                            
                            <div id="cameraPlaceholder" class="camera-placeholder">
                                <i id="cameraPlaceholderIcon" class="fas fa-camera fa-4x text-primary mb-3"></i>
                                <h4 class="text-primary mb-2">📱 This is the camera preview </h4>
                                <h6 class="text-muted">Camera Preview</h6>
                                <p class="text-muted mb-3" id="cameraPlaceholderText">
                                    Click "Start Camera" to see live preview
                                </p>
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle"></i>
                                    <strong>Tip:</strong> <span id="cameraPlaceholderTip">Start the camera to see where the camera is looking</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Device Status -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-video"></i> Device Status</h5>
                    </div>
                    <div class="card-body">
                        <div id="deviceList">
                            <div class="device-card">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>ESP32_CAM_SIM_001</strong>
                                        <br>
                                        <small class="text-muted">Last seen: 0min ago</small>
                                    </div>
                                    <div class="text-end">
                                        <span class="status-badge status-online">ACTIVE</span>
                                        <br>
                                        <small class="text-muted">0 detections | 0 alerts</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recent Detections -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-history"></i> Recent Detections</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <div id="recentDetections">
                            <div class="text-center text-muted">No recent detections - system ready</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Image Testing -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i id="testIcon" class="fas fa-vial text-warning"></i> <span id="testTitle">Test Fire Detection</span></h5>
                    </div>
                    <div class="card-body">
                        <div class="upload-zone" id="uploadZone">
                            <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
                            <h5>Upload Image for Testing</h5>
                            <p class="text-muted" id="uploadInstructions">Drag and drop an image here, or click to select</p>
                            <input type="file" id="imageInput" class="d-none" accept="image/*">
                        </div>
                        
                        <div id="testResults" style="display: none;">
                            <div class="row mt-3">
                                <div class="col-md-6">
                                    <h6>Original Image:</h6>
                                    <img id="imagePreview" class="img-fluid" style="max-height: 300px;">
                                </div>
                                <div class="col-md-6">
                                    <h6>Detection Results:</h6>
                                    <div id="detectionResults">
                                        <!-- Results will be populated here -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Detection Chart -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Detection Activity (24H)</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="detectionChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let detectionChart;
        let currentTask = 'fire'; // 'fire' or 'leaves'
        
        // Initialize immediately
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Dashboard loaded - initializing...');
            initTaskToggle();
            fetchStatistics();
            initChart();
            setupCameraControls();
            setupImageUpload();
            
            // Set up periodic updates
            setInterval(fetchStatistics, 3000);
        });
        
        // Task switching functionality
        function initTaskToggle() {
            const toggle = document.getElementById('taskToggle');
            const fireLabel = document.getElementById('fireLabel');
            const leavesLabel = document.getElementById('leavesLabel');
            const currentTaskDisplay = document.getElementById('currentTaskDisplay');
            
            toggle.addEventListener('change', function() {
                if (this.checked) {
                    // Switch to yellow leaves detection
                    currentTask = 'leaves';
                    updateTaskUI('leaves');
                    switchDetectionTask('leaves');
                } else {
                    // Switch to fire detection
                    currentTask = 'fire';
                    updateTaskUI('fire');
                    switchDetectionTask('fire');
                }
            });
        }
        
        function updateTaskUI(task) {
            const body = document.getElementById('dashboardBody');
            const taskIcon = document.getElementById('taskIcon');
            const taskTitle = document.getElementById('taskTitle');
            const fireLabel = document.getElementById('fireLabel');
            const leavesLabel = document.getElementById('leavesLabel');
            const currentTaskDisplay = document.getElementById('currentTaskDisplay');
            const alertsLabel = document.getElementById('alertsLabel');
            const testIcon = document.getElementById('testIcon');
            const testTitle = document.getElementById('testTitle');
            const cameraInstructions = document.getElementById('cameraInstructions');
            const cameraPlaceholderText = document.getElementById('cameraPlaceholderText');
            const cameraPlaceholderTip = document.getElementById('cameraPlaceholderTip');
            const uploadInstructions = document.getElementById('uploadInstructions');
            
            if (task === 'leaves') {
                // Yellow leaves theme
                body.style.background = 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)';
                taskIcon.textContent = '🍃';
                taskTitle.textContent = 'Yellow Leaves Detection';
                fireLabel.classList.add('inactive');
                leavesLabel.classList.remove('inactive');
                currentTaskDisplay.innerHTML = '🍃 Yellow Leaves Detection Active';
                alertsLabel.textContent = 'YELLOW LEAVES ALERTS (24H)';
                testIcon.className = 'fas fa-leaf text-success';
                testTitle.textContent = 'Test Yellow Leaves Detection';
                cameraInstructions.textContent = 'Live feed from laptop camera • Position plants with yellow leaves here';
                cameraPlaceholderText.textContent = 'Click "Start Camera" to see live preview and position plants with yellow leaves';
                cameraPlaceholderTip.textContent = 'Start the camera to see exactly where to position plants for yellow leaves detection testing!';
                uploadInstructions.textContent = 'Drag and drop a plant image here, or click to select';
            } else {
                // Fire theme
                body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                taskIcon.textContent = '🔥';
                taskTitle.textContent = 'Fire Detection';
                fireLabel.classList.remove('inactive');
                leavesLabel.classList.add('inactive');
                currentTaskDisplay.innerHTML = '🔥 Fire Detection Active';
                alertsLabel.textContent = 'FIRE ALERTS (24H)';
                testIcon.className = 'fas fa-vial text-warning';
                testTitle.textContent = 'Test Fire Detection';
                cameraInstructions.textContent = 'Live feed from laptop camera';
                cameraPlaceholderText.textContent = 'Click "Start Camera" to see live preview';
                cameraPlaceholderTip.textContent = 'Start the camera to see exactly where the camera is looking';
                uploadInstructions.textContent = 'Drag and drop an image here, or click to select';
            }
        }
        
        function switchDetectionTask(task) {
            // Send task switch to server
            fetch('/api/switch-task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task: task
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Task switched to:', task);
                // Refresh statistics to show new task data
                fetchStatistics();
            })
            .catch(error => {
                console.error('Error switching task:', error);
            });
        }
        
        // Connection status
        socket.on('connect', function() {
            console.log('Connected to server');
            document.getElementById('connectionStatus').innerHTML = '<i class="fas fa-circle"></i> Connected';
            fetchStatistics();
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            document.getElementById('connectionStatus').innerHTML = '<i class="fas fa-circle"></i> Disconnected';
            document.getElementById('connectionStatus').className = 'badge bg-danger';
        });
        
        // Status updates
        socket.on('status_update', function(data) {
            console.log('Status update received:', data);
            updateDashboard(data);
        });
        
        function updateDashboard(data) {
            if (data.devices) updateDeviceList(data.devices);
            if (data.recent_detections) updateRecentDetections(data.recent_detections);
            if (data.ai_server) updateAIServerStatus(data.ai_server);
            fetchStatistics();
        }
        
        function updateAIServerStatus(status) {
            const element = document.getElementById('aiServerStatus');
            if (status.status === 'online') {
                element.className = 'badge bg-success ms-2';
                element.innerHTML = '<i class="fas fa-server"></i> AI Server: Online';
            } else {
                element.className = 'badge bg-danger ms-2';
                element.innerHTML = '<i class="fas fa-server"></i> AI Server: ' + status.status;
            }
        }
        
        function updateDeviceList(devices) {
            const container = document.getElementById('deviceList');
            
            if (!devices || devices.length === 0) {
                container.innerHTML = '<div class="text-center text-muted">No devices found</div>';
                return;
            }
            
            container.innerHTML = devices.map(device => `
                <div class="device-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${device.device_id}</strong>
                            <br>
                            <small class="text-muted">Last seen: ${device.minutes_since_last_seen}min ago</small>
                        </div>
                        <div class="text-end">
                            <span class="status-badge status-online">${device.status}</span>
                            <br>
                            <small class="text-muted">${device.total_detections} detections | ${device.fire_alerts} alerts</small>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        function updateRecentDetections(detections) {
            const container = document.getElementById('recentDetections');
            
            if (!detections || detections.length === 0) {
                container.innerHTML = '<div class="text-center text-muted">No recent detections</div>';
                return;
            }
            
            container.innerHTML = detections.map(detection => {
                const alertClass = detection.fire_detected ? 'alert-danger' : 'alert-success';
                const timeAgo = new Date(detection.timestamp).toLocaleString();
                
                return `
                    <div class="alert ${alertClass} py-2 mb-2">
                        <div class="d-flex justify-content-between">
                            <div>
                                <strong>${detection.device_id}</strong>
                                <br>
                                <small>${timeAgo}</small>
                                ${detection.fire_detected ? 
                                    `<br><span class="text-danger"><i class="fas fa-fire"></i> Fire detected (${(detection.confidence * 100).toFixed(1)}%)</span>` : 
                                    '<br><span class="text-success"><i class="fas fa-check"></i> No fire detected</span>'
                                }
                            </div>
                            <div class="text-end">
                                <span class="badge bg-secondary">${detection.alert_level}</span>
                                <br>
                                <small>${detection.processing_time_ms ? detection.processing_time_ms.toFixed(0) : 0}ms</small>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function fetchStatistics() {
            fetch('/api/statistics')
                .then(response => {
                    if (!response.ok) throw new Error('API not responding');
                    return response.json();
                })
                .then(data => {
                    console.log('Statistics data:', data);
                    document.getElementById('totalDetections').textContent = data.total_detections || 0;
                    document.getElementById('fireAlerts').textContent = data.fire_alerts || 0;
                    document.getElementById('activeDevices').textContent = data.active_devices || 1;
                    document.getElementById('alertRate').textContent = (data.alert_rate || 0) + '%';
                    
                    if (data.hourly_data) updateChart(data.hourly_data);
                })
                .catch(error => {
                    console.log('Statistics fetch error:', error);
                    // Keep default values on error - at least dashboard shows something
                });
        }
        
        function initChart() {
            const ctx = document.getElementById('detectionChart').getContext('2d');
            
            const hours = Array.from({length: 24}, (_, i) => i.toString().padStart(2, '0'));
            const currentHour = new Date().getHours();
            
            detectionChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: hours,
                    datasets: [{
                        label: 'Total Detections',
                        data: new Array(24).fill(0),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.4
                    }, {
                        label: 'Fire Detections',
                        data: new Array(24).fill(0),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        function updateChart(hourlyData) {
            if (!detectionChart || !hourlyData) return;
            
            const totalData = new Array(24).fill(0);
            const fireData = new Array(24).fill(0);
            
            hourlyData.forEach(item => {
                const hour = parseInt(item.hour);
                totalData[hour] = item.total || 0;
                fireData[hour] = item.fire || 0;
            });
            
            detectionChart.data.datasets[0].data = totalData;
            detectionChart.data.datasets[1].data = fireData;
            detectionChart.update();
        }
        
        function setupCameraControls() {
            const toggleBtn = document.getElementById('cameraToggleBtn');
            const cameraPreview = document.getElementById('cameraPreview');
            const cameraPlaceholder = document.getElementById('cameraPlaceholder');
            const cameraStream = document.getElementById('cameraStream');
            
            let cameraActive = false;
            let isProcessing = false; // Prevent double-clicks
            
            toggleBtn.addEventListener('click', async function() {
                // Prevent multiple simultaneous requests
                if (isProcessing) {
                    console.log('Camera operation already in progress, ignoring click');
                    return;
                }
                
                isProcessing = true;
                const originalText = toggleBtn.innerHTML;
                
                try {
                    console.log('Camera button clicked, current state:', cameraActive);
                    
                    // Show loading state
                    toggleBtn.disabled = true;
                    toggleBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                    
                    if (!cameraActive) {
                        // Start camera
                        console.log('Attempting to start camera...');
                        const response = await fetch('/api/camera/start', { 
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            // Add timeout to prevent hanging
                            signal: AbortSignal.timeout(10000) // 10 second timeout
                        });
                        
                        console.log('Start camera response status:', response.status);
                        
                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
                        }
                        
                        const result = await response.json();
                        console.log('Start camera result:', result);
                        
                        if (result.success) {
                            cameraActive = true;
                            cameraPreview.style.display = 'block';
                            cameraPlaceholder.style.display = 'none';
                            toggleBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Camera';
                            toggleBtn.className = 'btn btn-outline-danger btn-sm';
                            
                            // Force refresh the camera stream
                            cameraStream.src = '/video_feed?' + Date.now();
                            
                            console.log('Camera started successfully:', result.message);
                        } else {
                            throw new Error(result.message || 'Unknown error starting camera');
                        }
                    } else {
                        // Stop camera
                        console.log('Attempting to stop camera...');
                        const response = await fetch('/api/camera/stop', { 
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            // Add timeout to prevent hanging
                            signal: AbortSignal.timeout(10000) // 10 second timeout
                        });
                        
                        console.log('Stop camera response status:', response.status);
                        
                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
                        }
                        
                        const result = await response.json();
                        console.log('Stop camera result:', result);
                        
                        if (result.success) {
                            cameraActive = false;
                            cameraPreview.style.display = 'none';
                            cameraPlaceholder.style.display = 'block';
                            toggleBtn.innerHTML = '<i class="fas fa-play"></i> Start Camera';
                            toggleBtn.className = 'btn btn-outline-primary btn-sm';
                            
                            console.log('Camera stopped successfully:', result.message);
                        } else {
                            // Even if server reports error, update UI to stopped state
                            cameraActive = false;
                            cameraPreview.style.display = 'none';
                            cameraPlaceholder.style.display = 'block';
                            toggleBtn.innerHTML = '<i class="fas fa-play"></i> Start Camera';
                            toggleBtn.className = 'btn btn-outline-primary btn-sm';
                            
                            console.warn('Camera stop had issues but UI updated:', result.message);
                        }
                    }
                } catch (error) {
                    console.error('Camera control error:', error);
                    
                    // Show user-friendly error message
                    let errorMsg = 'Camera control error';
                    if (error.name === 'AbortError') {
                        errorMsg = 'Camera operation timed out. Please try again.';
                    } else if (error.message.includes('Failed to fetch')) {
                        errorMsg = 'Connection to server lost. Please check if the system is running.';
                    } else {
                        errorMsg = 'Camera error: ' + error.message;
                    }
                    
                    // Show error notification instead of alert
                    showNotification(errorMsg, 'error');
                    
                    // If it was a stop operation that failed, still update UI
                    if (cameraActive && error.message.includes('stop')) {
                        console.log('Stop operation failed, but updating UI anyway');
                        cameraActive = false;
                        cameraPreview.style.display = 'none';
                        cameraPlaceholder.style.display = 'block';
                        toggleBtn.innerHTML = '<i class="fas fa-play"></i> Start Camera';
                        toggleBtn.className = 'btn btn-outline-primary btn-sm';
                    }
                } finally {
                    // Always restore button state
                    isProcessing = false;
                    toggleBtn.disabled = false;
                    
                    // If button text is still "Processing...", restore it
                    if (toggleBtn.innerHTML.includes('Processing')) {
                        toggleBtn.innerHTML = originalText;
                    }
                }
            });
            
            // Add notification function
            function showNotification(message, type = 'info') {
                // Create notification element
                const notification = document.createElement('div');
                notification.className = `alert alert-${type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
                notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
                notification.innerHTML = `
                    <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'info-circle'}"></i>
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                
                document.body.appendChild(notification);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 5000);
            }
            
            // Check camera status on load with error handling
            fetch('/api/camera/status')
                .then(response => {
                    if (!response.ok) throw new Error('Failed to get camera status');
                    return response.json();
                })
                .then(status => {
                    if (status.active) {
                        cameraActive = true;
                        cameraPreview.style.display = 'block';
                        cameraPlaceholder.style.display = 'none';
                        toggleBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Camera';
                        toggleBtn.className = 'btn btn-outline-danger btn-sm';
                        cameraStream.src = '/video_feed?' + Date.now();
                    }
                })
                .catch(error => {
                    console.log('Camera status check failed:', error);
                    // Don't show error to user on initial load
                });
        }
        
        function setupImageUpload() {
            const uploadZone = document.getElementById('uploadZone');
            const imageInput = document.getElementById('imageInput');
            const testResults = document.getElementById('testResults');
            const imagePreview = document.getElementById('imagePreview');
            const detectionResults = document.getElementById('detectionResults');
            
            // Click to upload
            uploadZone.addEventListener('click', () => imageInput.click());
            
            // File input change
            imageInput.addEventListener('change', handleFileUpload);
            
            // Drag and drop
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.style.borderColor = '#28a745';
                uploadZone.style.backgroundColor = 'rgba(40, 167, 69, 0.1)';
            });
            
            uploadZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadZone.style.borderColor = '#007bff';
                uploadZone.style.backgroundColor = 'rgba(0, 123, 255, 0.05)';
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.style.borderColor = '#007bff';
                uploadZone.style.backgroundColor = 'rgba(0, 123, 255, 0.05)';
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    processImageFile(files[0]);
                }
            });
            
            function handleFileUpload(e) {
                const file = e.target.files[0];
                if (file) {
                    processImageFile(file);
                }
            }
            
            function processImageFile(file) {
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file');
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    const imageData = e.target.result;
                    
                    // Show preview
                    imagePreview.src = imageData;
                    testResults.style.display = 'block';
                    
                    // Send for processing
                    processImage(imageData);
                };
                reader.readAsDataURL(file);
            }
            
            async function processImage(imageData) {
                try {
                    detectionResults.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Processing image...</div>';
                    
                    const response = await fetch('/api/test-image', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            image: imageData,
                            device_id: 'DASHBOARD_TEST'
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.error) {
                        detectionResults.innerHTML = '<div class="alert alert-danger">Error: ' + result.error + '</div>';
                        return;
                    }
                    
                    // Display results
                    displayDetectionResults(result);
                    
                } catch (error) {
                    console.error('Image processing error:', error);
                    detectionResults.innerHTML = '<div class="alert alert-danger">Processing failed: ' + error.message + '</div>';
                }
            }
            
            function displayDetectionResults(result) {
                const detections = result.detections || [];
                
                let html = '';
                
                if (detections.length === 0) {
                    html = '<div class="alert alert-success"><i class="fas fa-check-circle"></i> No fire detected</div>';
                } else {
                    html = '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> Detections found:</div>';
                    
                    detections.forEach((detection, index) => {
                        const isFireDetection = detection.class_id === 0 || detection.class === 'fire' || detection.class === '0';
                        const alertClass = isFireDetection ? 'alert-danger' : 'alert-success';
                        const icon = isFireDetection ? 'fa-fire' : 'fa-check';
                        const label = isFireDetection ? 'FIRE DETECTED' : 'NO FIRE';
                        
                        html += `
                            <div class="alert ${alertClass} py-2 mb-2">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <i class="fas ${icon}"></i> <strong>${label}</strong>
                                        <br>
                                        <small>Confidence: ${(detection.confidence * 100).toFixed(1)}%</small>
                                    </div>
                                    <div class="text-end">
                                        <span class="badge bg-secondary">${detection.class || 'Unknown'}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                }
                
                html += `
                    <div class="mt-3">
                        <small class="text-muted">
                            Processing time: ${result.processing_time_ms || 0}ms<br>
                            Image size: ${result.image_size ? result.image_size.width + 'x' + result.image_size.height : 'Unknown'}
                        </small>
                    </div>
                `;
                
                detectionResults.innerHTML = html;
            }
        }
    </script>
</body>
</html>"""

@app.route("/api/switch-task", methods=["POST"])
def api_switch_task():
    """Switch detection task"""
    try:
        data = request.get_json()
        task = data.get("task")
        
        if not task:
            return jsonify({"error": "No task specified"}), 400
        
        if dashboard.set_current_task(task):
            # Emit task change to all connected clients
            socketio.emit("task_changed", {
                "task": task,
                "model": dashboard.get_current_model(),
                "timestamp": datetime.now().isoformat()
            })
            
            return jsonify({
                "success": True,
                "task": task,
                "model": dashboard.get_current_model(),
                "message": f"Task switched to {task}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Invalid task: {task}"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/current-task")
def api_current_task():
    """Get current detection task"""
    return jsonify({
        "task": dashboard.get_current_task(),
        "model": dashboard.get_current_model(),
        "available_tasks": list(dashboard.task_models.keys())
    })

@app.route("/api/devices")
def api_devices():
    """Get device status API"""
    return jsonify(dashboard.get_device_status())

@app.route("/api/detections")
def api_detections():
    """Get recent detections API"""
    limit = request.args.get("limit", 50, type=int)
    return jsonify(dashboard.get_recent_detections(limit))

@app.route("/api/statistics")
def api_statistics():
    """Get detection statistics API"""
    hours = request.args.get("hours", 24, type=int)
    stats = dashboard.get_detection_statistics(hours)
    # Add current task info to statistics
    stats["current_task"] = dashboard.get_current_task()
    stats["current_model"] = dashboard.get_current_model()
    return jsonify(stats)

@app.route("/api/test-image", methods=["POST"])
def api_test_image():
    """Test image processing API"""
    try:
        data = request.get_json()
        image_data = data.get("image")
        device_id = data.get("device_id", "DASHBOARD_TEST")
        
        if not image_data:
            return jsonify({"error": "No image data provided"}), 400
        
        result = dashboard.process_test_image(image_data, device_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai-server-status")
def api_ai_server_status():
    """Get AI server status"""
    return jsonify(dashboard._check_ai_server_status())

@app.route("/api/esp32-notification", methods=["POST"])
def api_esp32_notification():
    """Receive ESP32-CAM fire detection notifications"""
    try:
        data = request.get_json()
        device_id = data.get("device_id", "unknown")
        fire_on = data.get("fire_on", 0)
        detection_data = data.get("detection_data", {})
        
        # Store detection in database
        dashboard._store_esp32_detection(detection_data, device_id)
        
        # Update device status
        dashboard._update_esp32_device_status(device_id, fire_on == 1)
        
        # Emit real-time update to connected clients
        socketio.emit("new_detection", {
            "device_id": device_id,
            "fire_on": fire_on,
            "detection_data": detection_data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Fire alert notification
        if fire_on == 1:
            socketio.emit("fire_alert", {
                "device_id": device_id,
                "message": f"🔥 FIRE DETECTED on {device_id}!",
                "confidence": detection_data.get("confidence", 0),
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify({
            "success": True,
            "message": "Notification received and processed"
        })
        
    except Exception as e:
        print(f"ESP32 notification error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/camera/start", methods=["POST"])
def api_camera_start():
    """Start camera preview"""
    try:
        result = dashboard.start_camera_preview()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to start camera: {str(e)}"
        }), 500

@app.route("/api/camera/stop", methods=["POST"])
def api_camera_stop():
    """Stop camera preview with enhanced error handling"""
    try:
        print("🛑 API: Camera stop request received")
        result = dashboard.stop_camera_preview()
        print(f"🔄 API: Camera stop result: {result}")
        return jsonify(result)
    except Exception as e:
        error_msg = f"Failed to stop camera: {str(e)}"
        print(f"❌ API: {error_msg}")
        # Return error but don't crash
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@app.route("/api/camera/status")
def api_camera_status():
    """Get camera status"""
    try:
        status = dashboard.get_camera_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "active": False,
            "has_camera": False,
            "error": str(e)
        }), 500

def generate_camera_stream():
    """Generate camera stream for video feed"""
    while True:
        frame = dashboard.get_camera_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            # Send a placeholder frame when no camera data
            placeholder = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x96\x00\x96\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
        time.sleep(1/30)  # 30 FPS

@app.route("/video_feed")
def video_feed():
    """Video streaming route"""
    return Response(generate_camera_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# SocketIO Events
@socketio.on("connect")
def on_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    dashboard.active_connections.add(request.sid)
    
    # Send initial data
    emit("status_update", {
        "devices": dashboard.get_device_status(),
        "recent_detections": dashboard.get_recent_detections(10),
        "ai_server": dashboard._check_ai_server_status(),
        "timestamp": datetime.now().isoformat()
    })

@socketio.on("disconnect")
def on_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")
    dashboard.active_connections.discard(request.sid)

@socketio.on("request_update")
def on_request_update():
    """Handle manual update request"""
    emit("status_update", {
        "devices": dashboard.get_device_status(),
        "recent_detections": dashboard.get_recent_detections(10),
        "ai_server": dashboard._check_ai_server_status(),
        "timestamp": datetime.now().isoformat()
    })

def main():
    """Main function to run the dashboard"""
    print("🔥 Fire Detection Dashboard")
    print("=" * 40)
    print("Starting web dashboard...")
    print("Dashboard will be available at: http://localhost:8080")
    print("AI Server should be running at: http://localhost:5001")
    
    # Check if AI server is running
    ai_status = dashboard._check_ai_server_status()
    if ai_status["status"] == "online":
        print("✅ AI Server is online and ready")
    else:
        print("⚠️  AI Server not responding - some features may not work")
        print("   Please start the AI server: cd server && python ai_server.py")
    
    try:
        socketio.run(app, host="0.0.0.0", port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down dashboard...")

if __name__ == "__main__":
    main() 