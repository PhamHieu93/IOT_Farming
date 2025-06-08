#!/usr/bin/env python3
"""
AI Server for ESP32-CAM Object Detection
Receives images from ESP32-CAM and processes them using YOLO models

Setup:
1. pip install flask ultralytics pillow opencv-python
2. Download your trained YOLO model (best.pt) to models/ directory
3. Run: python ai_server.py

API Endpoints:
- POST /api/detect - Process image for object detection
- GET /api/status - Get server status
- GET /api/models - List available models
"""

import os
import base64
import time
import cv2
import numpy as np
import gc
import torch
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify
from ultralytics import YOLO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    "models_dir": "models",
    "default_model": "fire_detect_final.pt",
    "max_image_size": 5 * 1024 * 1024,  # 5MB
    "supported_formats": [".jpg", ".jpeg", ".png"],
    "default_confidence": 0.5,
    "max_detections": 100,
    "task_models": {
        "fire": "fire_detection_final",
        "leaves": "yellow-leaves-best"
    },
    "task_thresholds": {
        "fire": 0.15,
        "leaves": 0.6
    }
}

# Global model storage
models = {}

# Request counter for memory management
request_counter = 0
last_model_reload = 0

def load_models():
    """Load all available YOLO models"""
    models_dir = CONFIG["models_dir"]
    
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        logger.warning(f"Created {models_dir} directory. Please add your YOLO models here.")
        return
    
    for filename in os.listdir(models_dir):
        if filename.endswith(".pt"):
            model_path = os.path.join(models_dir, filename)
            try:
                model = YOLO(model_path)
                model_name = filename.replace(".pt", "")
                models[model_name] = model
                logger.info(f"Loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {filename}: {e}")

def decode_base64_image(base64_string):
    """Decode base64 image string to PIL Image"""
    try:
        # Remove data URL prefix if present
        if "data:image/" in base64_string:
            base64_string = base64_string.split(",")[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        return image
    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")

def image_to_numpy(image):
    """Convert PIL Image to numpy array for YOLO"""
    return np.array(image)

def process_yolo_results(results, confidence_threshold=0.5):
    """Process YOLO detection results"""
    detections = []
    
    for result in results:
        if result.boxes is not None:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                confidence = float(boxes.conf[i])
                
                if confidence >= confidence_threshold:
                    # Get class information
                    class_id = int(boxes.cls[i])
                    class_name = result.names[class_id]
                    
                    # Get bounding box (xyxy format)
                    bbox = boxes.xyxy[i].tolist()
                    x1, y1, x2, y2 = bbox
                    
                    detection = {
                        "class": class_name,
                        "class_id": class_id,
                        "confidence": round(confidence, 3),
                        "bbox": {
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2),
                            "width": int(x2 - x1),
                            "height": int(y2 - y1),
                            "center_x": int((x1 + x2) / 2),
                            "center_y": int((y1 + y2) / 2)
                        }
                    }
                    detections.append(detection)
    
    return detections

@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    return jsonify({
        "message": "ESP32-CAM AI Server",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "This help message",
            "GET /api/status": "Server status and loaded models",
            "GET /api/models": "Available models and their classes",
            "GET /api/health": "Health check",
            "POST /api/detect": "Object detection (requires JSON with base64 image)"
        },
        "usage": {
            "test_status": "curl http://localhost:5001/api/status",
            "test_models": "curl http://localhost:5001/api/models",
            "run_full_test": "python test_system.py"
        },
        "models_loaded": len(models),
        "available_models": list(models.keys()) if models else []
    })

@app.route("/api/status", methods=["GET"])
def get_status():
    """Get server status"""
    global request_counter, last_model_reload
    
    status_info = {
        "status": "online",
        "models_loaded": len(models),
        "available_models": list(models.keys()),
        "server_time": time.time(),
        "config": CONFIG,
        "request_count": request_counter,
        "memory_info": {
            "cleanup_interval": 20,  # Updated to reflect new interval
            "next_cleanup_at": ((request_counter // 20) + 1) * 20,
            "requests_until_cleanup": ((request_counter // 20) + 1) * 20 - request_counter,
            "model_reload_interval": 100,
            "last_model_reload": last_model_reload,
            "requests_since_model_reload": request_counter - last_model_reload,
            "next_model_reload_at": last_model_reload + 100
        }
    }
    
    # Add GPU info if available
    if torch.cuda.is_available():
        status_info["gpu_info"] = {
            "available": True,
            "device_count": torch.cuda.device_count(),
            "current_device": torch.cuda.current_device(),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "Unknown"
        }
    else:
        status_info["gpu_info"] = {"available": False}
    
    return jsonify(status_info)

@app.route("/api/models", methods=["GET"])
def get_models():
    """Get list of available models"""
    model_info = {}
    for name, model in models.items():
        model_info[name] = {
            "class_names": list(model.names.values()),
            "num_classes": len(model.names)
        }
    
    return jsonify({
        "models": model_info,
        "default_model": CONFIG["default_model"].replace(".pt", "")
    })

@app.route("/api/detect", methods=["POST"])
def detect_objects():
    """Main object detection endpoint"""
    global request_counter
    
    try:
        # Increment request counter and check for memory cleanup
        request_counter += 1
        
        # More aggressive memory cleanup every 20 requests (instead of 50)
        if request_counter % 20 == 0:
            logger.info(f"🧹 Performing memory cleanup at request #{request_counter}")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"✅ Memory cleanup completed")
        
        # Check if we need to reload models to prevent memory leaks
        reload_models_if_needed()
        
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Required fields
        if "image" not in data:
            return jsonify({"error": "No image provided"}), 400
        
        # Optional parameters
        model_name = data.get("model", CONFIG["default_model"].replace(".pt", ""))
        confidence_threshold = data.get("threshold", CONFIG["default_confidence"])
        device_id = data.get("device_id", "unknown")
        
        # Validate model
        if model_name not in models:
            available_models = list(models.keys())
            return jsonify({
                "error": f"Model '{model_name}' not found",
                "available_models": available_models
            }), 400
        
        # Process image
        start_time = time.time()
        
        # Decode image
        try:
            image = decode_base64_image(data["image"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Convert to numpy array
        image_array = image_to_numpy(image)
        
        # Run inference
        model = models[model_name]
        results = model.predict(
            image_array,
            conf=confidence_threshold,
            verbose=False
        )
        
        # Process results
        detections = process_yolo_results(results, confidence_threshold)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Prepare response
        response = {
            "detections": detections,
            "processing_time_ms": round(processing_time, 2),
            "model_used": model_name,
            "confidence_threshold": confidence_threshold,
            "image_size": {
                "width": image.width,
                "height": image.height
            },
            "device_id": device_id,
            "timestamp": time.time(),
            "detection_count": len(detections),
            "request_count": request_counter  # Add request counter to response
        }
        
        # Add special alerts for critical detections
        critical_classes = ["fire", "smoke", "person", "danger"]
        high_confidence_detections = [
            d for d in detections 
            if d["confidence"] > 0.8 and d["class"].lower() in critical_classes
        ]
        
        if high_confidence_detections:
            response["alerts"] = []
            for detection in high_confidence_detections:
                alert = {
                    "type": detection["class"].upper() + "_DETECTED",
                    "severity": "HIGH" if detection["confidence"] > 0.9 else "MEDIUM",
                    "confidence": detection["confidence"],
                    "recommended_action": get_recommended_action(detection["class"])
                }
                response["alerts"].append(alert)
        
        logger.info(f"Processed image from {device_id}: {len(detections)} detections in {processing_time:.2f}ms (Request #{request_counter})")
        
        # More aggressive cleanup - delete all intermediate variables
        del image, image_array, results, detections
        if 'high_confidence_detections' in locals():
            del high_confidence_detections
        
        # Force garbage collection after every request when approaching problematic range
        if request_counter > 200:
            gc.collect()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

def get_recommended_action(object_class):
    """Get recommended action for detected object"""
    actions = {
        "fire": "Immediate evacuation and fire suppression",
        "smoke": "Investigate source and prepare for evacuation",
        "person": "Monitor activity and verify authorization",
        "vehicle": "Check for authorized access",
        "animal": "Monitor behavior and ensure safety",
        "default": "Monitor situation and take appropriate action"
    }
    
    return actions.get(object_class.lower(), actions["default"])

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

def reload_models_if_needed():
    """Reload models periodically to prevent memory leaks"""
    global last_model_reload, models
    
    # Reload models every 100 requests to clear accumulated memory
    if request_counter - last_model_reload >= 100:
        logger.info(f"🔄 Reloading models at request #{request_counter} to clear memory")
        try:
            # Clear existing models
            for model_name in list(models.keys()):
                del models[model_name]
            models.clear()
            
            # Force garbage collection
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Reload models
            load_models()
            last_model_reload = request_counter
            logger.info(f"✅ Models reloaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Model reload failed: {e}")
            # Try to reload just the default model if full reload fails
            try:
                load_models()
            except:
                pass

if __name__ == "__main__":
    print("=== ESP32-CAM AI Server ===")
    print("Loading YOLO models...")
    
    load_models()
    
    if not models:
        print("WARNING: No models loaded!")
        print(f"Please add YOLO model files (.pt) to the '{CONFIG['models_dir']}' directory")
        print("Example: models/fire_detection_best.pt")
    else:
        print(f"Loaded {len(models)} model(s): {list(models.keys())}")
    
    print("\nAPI Endpoints:")
    print("- POST /api/detect - Object detection")
    print("- GET /api/status - Server status")
    print("- GET /api/models - Available models")
    print("- GET /api/health - Health check")
    
    print("\nStarting server on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=False) 