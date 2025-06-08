# 🔥🍃 Complete ESP32-CAM Dual Detection System

A comprehensive real-time **fire and yellow leaf detection system** using ESP32-CAM, dual YOLO AI models, and web-based monitoring dashboard with task switching capabilities.

## 🌟 System Overview

This project provides a complete end-to-end dual detection solution:

1. **ESP32-CAM Device** - Captures images and sends to AI server
2. **Dual AI Server** - Processes images using trained YOLO models for both fire and yellow leaf detection  
3. **Real-time Dashboard** - Web interface with task switching between fire and yellow leaf detection
4. **Task Management** - Dynamic switching between detection tasks without system restart
5. **Database Storage** - SQLite database with independent counters for each detection type

## 🎯 Detection Tasks

### 🔥 Fire Detection Task
- **Model**: `fire_detection_final.pt`
- **Purpose**: Detects fire and flames in real-time
- **Confidence Threshold**: 0.15 (highly sensitive)
- **Alert Levels**: CRITICAL/HIGH/MEDIUM/LOW based on confidence
- **Use Cases**: Forest fire monitoring, building fire safety, industrial fire detection

### 🍃 Yellow Leaf Detection Task  
- **Model**: `yellow-leaves-best.pt`
- **Purpose**: Detects yellow/diseased leaves on plants
- **Confidence Threshold**: 0.6 (precise detection)
- **Classes**: Yellow leaves vs Non-yellow leaves
- **Use Cases**: Plant health monitoring, agricultural disease detection, crop management

## 🚀 Quick Start

### Option 1: Automated Launch (Recommended)

```bash
# Navigate to the project directory
cd WebApp_IOT/YOLO-AI_Detection

# Run the complete dual-task system launcher
python start_complete_system.py
```

This will automatically:
- ✅ Check all dependencies
- ✅ Install required packages  
- ✅ Load both AI models (fire + yellow leaf detection)
- ✅ Start AI server (port 5001) with dual model support
- ✅ Start dashboard (port 8080) with task switching
- ✅ Start ESP32-CAM simulator with task awareness
- ✅ Run system tests for both detection types
- ✅ Display access URLs

### Option 2: Manual Launch

```bash
# Terminal 1: Start Dual AI Server
cd server
source ai_server_env/bin/activate  # if using virtual environment
python ai_server.py

# Terminal 2: Start Dashboard with Task Switching
cd ..
python fire_detection_dashboard.py

# Terminal 3: Start ESP32-CAM Simulator
python esp32_cam_simulator.py
```

## 📊 Access the System

Once running, access these URLs:

- **🔥🍃 Dual Detection Dashboard**: http://localhost:8080
- **🤖 AI Server API**: http://localhost:5001
- **📈 API Status**: http://localhost:5001/api/status
- **🔄 Task Switching**: Available in dashboard interface

## 🔧 System Components

### 1. Dual AI Server (`server/ai_server.py`)
- **Port**: 5001
- **Function**: Processes images using dual YOLO detection models
- **Models**: 
  - `fire_detection_final.pt` - Fire detection model
  - `yellow-leaves-best.pt` - Yellow leaf detection model
- **Task Management**: Dynamic model switching based on current task
- **API Endpoints**:
  - `POST /api/detect` - Process image with current task model
  - `GET /api/status` - Server health and loaded models status
  - `GET /api/models` - Available models and their classes
  - `GET /api/health` - Health check

### 2. Real-time Dashboard with Task Switching (`fire_detection_dashboard.py`)
- **Port**: 8080
- **Function**: Web-based monitoring interface with dual-task support
- **Task Switching**: Dynamic switching between fire and yellow leaf detection
- **Features**:
  - ✅ **Task Selection**: Switch between fire and yellow leaf detection modes
  - ✅ **Independent Counters**: Separate statistics for each detection type
  - ✅ **Real-time Updates**: Live detection feed with WebSocket updates
  - ✅ **Themed Interface**: Fire theme (red/orange) and leaf theme (green)
  - ✅ **Live Camera Preview**: Laptop camera integration for both tasks
  - ✅ **Image Upload Testing**: Test both detection types via drag & drop
  - ✅ **Responsive UI**: Modern Bootstrap 5 interface with task-specific styling

### 3. ESP32-CAM Simulator (`esp32_cam_simulator.py`)
- **Function**: Simulates ESP32-CAM behavior with dual-task awareness
- **Task Synchronization**: Automatically syncs with dashboard's current task
- **Camera Sources**: 
  - Laptop camera (real-time capture)
  - Test image dataset (simulation mode)
- **Features**:
  - ✅ **Task-Aware Processing**: Uses appropriate model based on current task
  - ✅ **Dynamic Task Switching**: Switches detection logic without restart
  - ✅ **Independent Alert System**: Separate fire/leaf detection alerts
  - ✅ **Real-time Notifications**: Sends task-specific alerts to dashboard

### 4. ESP32-CAM Code (`src/hybrid_ai_processing.cpp`)
- **Function**: Camera firmware for ESP32-CAM devices
- **Task Support**: Configurable for either fire or yellow leaf detection
- **Features**:
  - ✅ WiFi connectivity
  - ✅ Camera image capture (configurable resolution)
  - ✅ Base64 image encoding
  - ✅ HTTP POST to AI server with task specification
  - ✅ Task-specific LED indicators
  - ✅ MQTT publishing for task-based alerts

## 🔄 Task Switching Workflow

### Dashboard Task Switching
1. **Open Dashboard**: http://localhost:8080
2. **Select Task**: Click either "🔥 Fire Detection" or "🍃 Yellow Leaves Detection" 
3. **Auto-Switch**: Dashboard immediately switches to selected task
4. **Theme Change**: Interface changes color theme (red for fire, green for leaves)
5. **Model Update**: AI server automatically uses appropriate model
6. **Independent Stats**: Counters and statistics remain separate per task

### Automatic Synchronization
- **ESP32 Simulator**: Automatically detects dashboard task and switches accordingly
- **Real ESP32-CAM**: Can be configured to follow dashboard task or run independently
- **Database**: Maintains separate counters and history for each detection type

## 🔥🍃 Testing Both Detection Types

### Method 1: Dashboard Upload Testing

#### Fire Detection Test:
1. **Select Fire Task**: Click "🔥 Fire Detection" in dashboard
2. **Upload Fire Image**: Drag & drop fire/flame images
3. **View Results**: See fire detection with confidence scores

#### Yellow Leaf Detection Test:
1. **Select Leaves Task**: Click "🍃 Yellow Leaves Detection" in dashboard  
2. **Upload Plant Image**: Drag & drop plant images with yellow/diseased leaves
3. **View Results**: See yellow leaf detection with classification results

### Method 2: Live Camera Testing

1. **Start Camera**: Click "Start Camera" in dashboard
2. **Position Objects**: 
   - **Fire Task**: Position flame sources (candle, lighter, etc.)
   - **Leaves Task**: Position plants with yellow/diseased leaves
3. **Real-time Detection**: See live detection with bounding boxes
4. **Task Switching**: Switch tasks without stopping camera

### Method 3: ESP32-CAM Integration

1. **Flash ESP32-CAM** with `src/hybrid_ai_processing.cpp`
2. **Configure Task**: Set detection task in firmware or use dashboard sync
3. **Set AI Server URL**: Point to your server IP:5001
4. **Monitor Dashboard**: View real-time detections with task-specific alerts

## 📱 Enhanced Dashboard Features

### Task Management Interface
- **Task Selector**: Toggle between fire and yellow leaf detection
- **Visual Themes**: Color-coded interface (red/orange for fire, green for leaves)
- **Task Status**: Clear indication of currently active detection task
- **Independent Statistics**: Separate counters for each detection type

### Dual Detection Statistics
- **Fire Statistics**: Fire alerts, detection count, confidence scores
- **Leaf Statistics**: Yellow leaf detections, plant health metrics
- **Total System Stats**: Combined detection activity across both tasks
- **Task History**: Historical data preserved separately per task

### Enhanced Device Monitoring
- **Task-Aware Status**: Shows which task each device is running
- **Multi-Model Performance**: Processing times for both detection types
- **Task Switch Frequency**: Monitoring of task switching patterns

### Improved Detection Feed
- **Task-Specific Alerts**: Color-coded alerts based on detection type
- **Model Confidence**: Confidence scores specific to each model
- **Detection Context**: Clear indication of which model made each detection

## 🔧 Configuration

### Dual AI Server Configuration
Edit `server/ai_server.py`:
```python
CONFIG = {
    "task_models": {
        "fire": "fire_detection_final",        # Fire detection model
        "leaves": "yellow-leaves-best"         # Yellow leaf detection model  
    },
    "task_thresholds": {
        "fire": 0.15,                         # High sensitivity for fire
        "leaves": 0.6                         # Precision for leaf detection
    },
    "default_confidence": 0.5,
    "max_image_size": 5 * 1024 * 1024
}
```

### ESP32-CAM Configuration
Edit `src/hybrid_ai_processing.cpp`:
```cpp
#define WIFI_SSID "Your_WiFi_Name"
#define WIFI_PASSWORD "Your_WiFi_Password"
#define AI_SERVER_URL "http://your-server-ip:5001/api/detect"
#define CURRENT_TASK "fire"                   // "fire" or "leaves"
#define CAPTURE_INTERVAL 5000                 // 5 seconds
#define DETECTION_THRESHOLD_FIRE 0.15         // Fire sensitivity
#define DETECTION_THRESHOLD_LEAVES 0.6        // Leaf precision
```

### Dashboard Configuration
Edit `fire_detection_dashboard.py`:
```python
class FireDetectionDashboard:
    def __init__(self):
        self.ai_server_url = "http://localhost:5001"
        self.current_task = "fire"            # Default task
        self.task_models = {
            "fire": "fire_detection_final",
            "leaves": "yellow-leaves-best"
        }
```

## 📊 Enhanced Database Schema

The system uses SQLite database with task-aware tables:

### `fire_detections` (Enhanced)
- `id` - Auto-increment primary key
- `device_id` - ESP32-CAM device identifier
- **`task`** - Detection task ("fire" or "leaves")
- `timestamp` - Detection timestamp
- `fire_detected` - Boolean detection result (task-dependent)
- `confidence` - AI confidence score (0.0-1.0)
- `bbox` - JSON bounding box coordinates
- `image_size` - JSON image dimensions
- `processing_time_ms` - Processing time in milliseconds
- `alert_level` - Alert severity (task-specific)
- `image_data` - Base64 image thumbnail

### `device_status` (Enhanced)
- `device_id` - Primary key device identifier
- `last_seen` - Last communication timestamp
- `status` - Device status (ACTIVE/OFFLINE)
- `total_detections` - Combined detection count
- `fire_alerts` - Fire detection count
- **`fire_total_detections`** - Fire task detection count
- **`fire_alerts_count`** - Fire task alert count
- **`leaves_total_detections`** - Leaf task detection count  
- **`leaves_alerts_count`** - Leaf task alert count

## 🚨 Enhanced Alert System

### Fire Detection Alerts
- **CRITICAL** (>80% confidence): 🔴 Immediate fire emergency
- **HIGH** (60-80% confidence): 🟠 High fire risk alert  
- **MEDIUM** (40-60% confidence): 🟡 Possible fire detected
- **LOW** (15-40% confidence): 🟢 Fire signature detected
- **NONE** (no fire): ⚪ All clear

### Yellow Leaf Detection Alerts
- **YELLOW DETECTED** (>60% confidence): 🟡 Yellow/diseased leaves found
- **HEALTHY** (<60% confidence): 🟢 Healthy green leaves detected
- **NO LEAVES** (no detection): ⚪ No plant material detected

### Alert Channels
- ✅ **Task-Specific Notifications**: Alerts tailored to detection type
- ✅ **WebSocket Broadcasting**: Real-time updates for active task
- ✅ **Independent Logging**: Separate storage per detection type
- ✅ **Theme-Based UI**: Visual alerts matching current task theme

## 🚀 Enhanced Deployment Options

### Local Dual-Task Deployment
```bash
# Launch complete dual detection system
python start_complete_system.py

# Access both detection modes at http://localhost:8080
```

### Docker Deployment with Dual Models
```bash
# Build image with both models
docker build -t dual-detection-system .

# Run with model volume mounting
docker run -p 5001:5001 -p 8080:8080 \
  -v ./server/models:/app/server/models \
  dual-detection-system
```

### Production Multi-Task Deployment
- **Load Balancing**: Distribute detection tasks across multiple servers
- **Model Optimization**: Use TensorRT/ONNX for faster dual-model inference
- **Task Queuing**: Queue management for high-volume dual detection
- **Auto-Scaling**: Scale based on detection task demands

## 🔧 Task-Specific Troubleshooting

### Fire Detection Issues
```bash
# Test fire model specifically
curl -X POST http://localhost:5001/api/detect \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_fire_image", "task": "fire"}'

# Check fire model loading
grep "fire_detection_final" server/logs/ai_server.log
```

### Yellow Leaf Detection Issues  
```bash
# Test leaf model specifically
curl -X POST http://localhost:5001/api/detect \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_plant_image", "task": "leaves"}'

# Check leaf model loading
grep "yellow-leaves-best" server/logs/ai_server.log
```

### Task Switching Issues
- ✅ Verify both models are present in `server/models/`
- ✅ Check dashboard console for task switch confirmations
- ✅ Monitor ESP32 simulator logs for task synchronization
- ✅ Ensure database has task-specific columns

## 🎯 Enhanced Next Steps

### Multi-Task Enhancements
- [ ] **Additional Detection Tasks**: Add more plant disease detection models
- [ ] **Task Scheduling**: Automated task switching based on time/conditions
- [ ] **Hybrid Detection**: Simultaneous multi-task processing
- [ ] **Task Performance Analytics**: Compare model performance across tasks
- [ ] **Custom Task Creation**: User-defined detection tasks and models

### Production Multi-Task Features
- [ ] **Task Load Balancing**: Distribute different tasks across server instances  
- [ ] **Model Caching**: Intelligent model loading/unloading based on task frequency
- [ ] **Task-Specific Scaling**: Auto-scale resources based on task demands
- [ ] **Multi-Device Task Assignment**: Assign different devices to different tasks

## 📝 Model Training Notes

### Fire Detection Model (`fire_detection_final.pt`)
- **Dataset**: Fire/flame images with bounding box annotations
- **Classes**: Fire, No-fire
- **Training**: YOLOv8 with data augmentation
- **Optimization**: Tuned for high sensitivity (low false negatives)

### Yellow Leaf Detection Model (`yellow-leaves-best.pt`)  
- **Dataset**: Plant images with yellow/diseased leaf annotations
- **Classes**: Yellow leaves, Non-yellow leaves
- **Training**: YOLOv8 with plant-specific augmentation
- **Optimization**: Tuned for precision (low false positives)

## 🙏 Acknowledgments

- **Ultralytics YOLO**: For the excellent YOLO implementation supporting multiple models
- **ESP32 Community**: For Arduino libraries and examples
- **Bootstrap**: For the responsive UI framework with theming support
- **Chart.js**: For beautiful data visualization across detection types
- **Flask**: For the web framework with task management capabilities
- **Research Teams**: For fire detection and plant disease detection datasets

---

🔥🍃 **Ready to detect fires AND monitor plant health with AI!** 

Start with `python start_complete_system.py` and switch between detection tasks at http://localhost:8080 
