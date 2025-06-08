#!/usr/bin/env python3
"""
Complete Fire Detection System Startup Script
Launches all components including ESP32-CAM simulator
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path
import requests

class CompleteFireDetectionSystem:
    """Complete system launcher with ESP32-CAM simulation"""
    
    def __init__(self):
        """Initialize the complete system launcher"""
        self.processes = []
        self.base_dir = Path(__file__).parent
        self.server_dir = self.base_dir / "server"
        
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        print("🔍 Checking system dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ is required")
            return False
        
        # Check if required directories exist
        required_dirs = [
            self.server_dir,
            self.server_dir / "models",
            self.base_dir / "templates"
        ]
        
        # Skip test images directory check since we're using laptop camera only
        for dir_path in required_dirs:
            if not dir_path.exists():
                print(f"❌ Required directory missing: {dir_path}")
                return False
        
        # Check if fire detection model exists
        model_path = self.server_dir / "models" / "fire_detection_final.pt"
        if not model_path.exists():
            print(f"❌ Fire detection model not found: {model_path}")
            print("   Please copy your trained model to server/models/fire_detection_final.pt")
            return False
        
        # Check if required scripts exist
        required_scripts = [
            self.server_dir / "ai_server.py",
            self.base_dir / "fire_detection_dashboard.py",
            self.base_dir / "esp32_cam_simulator.py"
        ]
        
        for script_path in required_scripts:
            if not script_path.exists():
                print(f"❌ Required script not found: {script_path}")
                return False
        
        # Check camera availability
        print("📹 Checking laptop camera availability...")
        try:
            import cv2
            for camera_index in [0, 1, 2]:
                camera = cv2.VideoCapture(camera_index)
                if camera.isOpened():
                    ret, frame = camera.read()
                    camera.release()
                    if ret and frame is not None:
                        print(f"✅ Found working camera at index {camera_index}")
                        break
                else:
                    if camera:
                        camera.release()
            else:
                print("⚠️ No working camera found - camera features may not work")
        except Exception as e:
            print(f"⚠️ Camera check failed: {e}")
        
        print("✅ All dependencies checked successfully")
        return True
    
    def install_python_packages(self) -> bool:
        """Install required Python packages"""
        print("📦 Installing Python packages...")
        
        try:
            # Core packages for the system
            core_packages = [
                "flask>=2.3.0",
                "flask-socketio>=5.3.0",
                "ultralytics>=8.0.0",
                "opencv-python>=4.8.0",
                "pillow>=10.0.0",
                "requests>=2.31.0",
                "websockets>=11.0.3",
                "eventlet>=0.33.3",
                "python-socketio>=5.9.0"
            ]
            
            print("   Installing core packages...")
            failed_packages = []
            for package in core_packages:
                try:
                    subprocess.run([
                        sys.executable, "-m", "pip", "install", package
                    ], check=True, capture_output=True)
                    print(f"     ✅ {package}")
                except subprocess.CalledProcessError:
                    print(f"     ⚠️ Could not install {package}, continuing...")
                    failed_packages.append(package)
            
            # Install from requirements files if they exist (more forgiving)
            requirements_files = [
                self.server_dir / "requirements.txt",
                self.base_dir / "dashboard_requirements.txt"
            ]
            
            for req_file in requirements_files:
                if req_file.exists():
                    print(f"   Installing from {req_file.name}...")
                    try:
                        subprocess.run([
                            sys.executable, "-m", "pip", "install", "-r", str(req_file)
                        ], check=True, capture_output=True)
                        print(f"     ✅ {req_file.name}")
                    except subprocess.CalledProcessError as e:
                        print(f"     ⚠️ Some packages from {req_file.name} failed, continuing...")
            
            if failed_packages:
                print(f"   ⚠️ Some packages failed to install: {', '.join(failed_packages)}")
                print("   System may still work if packages are already installed")
            
            print("✅ Python packages installation completed")
            return True  # Continue even if some packages failed
            
        except Exception as e:
            print(f"❌ Package installation error: {e}")
            print("⚠️ Continuing anyway - packages may already be installed")
            return True  # Continue anyway
    
    def start_ai_server(self) -> subprocess.Popen:
        """Start the AI server"""
        print("🤖 Starting AI Server...")
        
        server_script = self.server_dir / "ai_server.py"
        
        process = subprocess.Popen(
            [sys.executable, str(server_script)],
            cwd=str(self.server_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Wait for server to start - increased timeout for model loading
        print("   Waiting for AI server to initialize (loading YOLO models)...")
        for attempt in range(30):  # Try for 30 seconds instead of 15
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                print("❌ AI Server process died")
                # Show output for debugging
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    if stdout:
                        print(f"   Process output: {stdout[-500:]}")  # Last 500 chars
                except:
                    pass
                return None
            
            try:
                response = requests.get("http://localhost:5001/api/status", timeout=3)
                if response.status_code == 200:
                    print("✅ AI Server started and responding (PID: {})".format(process.pid))
                    # Verify models are loaded
                    try:
                        data = response.json()
                        models_loaded = data.get("models_loaded", 0)
                        available_models = data.get("available_models", [])
                        print(f"   Loaded {models_loaded} models: {', '.join(available_models)}")
                    except:
                        pass
                    return process
                else:
                    print(f"   Server responding but not ready (status: {response.status_code}) - attempt {attempt+1}/30")
            except requests.exceptions.ConnectionError:
                if attempt % 5 == 0:  # Only print every 5 attempts to reduce spam
                    print(f"   Waiting for server to bind to port... (attempt {attempt+1}/30)")
            except Exception as e:
                if attempt % 5 == 0:
                    print(f"   Connection attempt failed: {type(e).__name__} - attempt {attempt+1}/30")
                continue
        
        print("❌ AI Server failed to respond after 30 seconds")
        print("   Attempting to read server output for debugging...")
        try:
            # Try to get output for debugging
            stdout, stderr = process.communicate(timeout=2)
            if stdout:
                print(f"   Server output: {stdout[-1000:]}")  # Last 1000 chars
        except:
            print("   Could not read server output")
        
        process.terminate()
        return None
    
    def start_dashboard(self) -> subprocess.Popen:
        """Start the dashboard server"""
        print("📊 Starting Fire Detection Dashboard...")
        
        # Use the working method that we just confirmed works
        dashboard_command = [
            sys.executable, "-c", 
            "from fire_detection_dashboard import app, socketio; socketio.run(app, host='0.0.0.0', port=8080, debug=False)"
        ]
        
        process = subprocess.Popen(
            dashboard_command,
            cwd=str(self.base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Wait for dashboard to start - increased timeout for statistics reset
        print("   Waiting for dashboard to initialize (including statistics reset)...")
        for attempt in range(15):  # Try for 15 seconds (increased from 10)
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                print("❌ Dashboard process died")
                return None
            
            try:
                # Test both statistics and AI server status endpoints
                response = requests.get("http://localhost:8080/api/statistics", timeout=3)
                if response.status_code == 200:
                    # Also test AI server status to ensure it's not hanging
                    try:
                        ai_response = requests.get("http://localhost:8080/api/ai-server-status", timeout=3)
                        if ai_response.status_code == 200:
                            print("✅ Dashboard started and responding with all endpoints (PID: {})".format(process.pid))
                            return process
                        else:
                            print(f"   Dashboard statistics OK, AI status check pending... (attempt {attempt+1}/15)")
                    except:
                        print(f"   Dashboard statistics OK, AI status check pending... (attempt {attempt+1}/15)")
                else:
                    print(f"   Dashboard initializing... (attempt {attempt+1}/15)")
            except:
                print(f"   Dashboard starting... (attempt {attempt+1}/15)")
                continue
        
        print("✅ Dashboard started (PID: {}) - may still be initializing some features".format(process.pid))
        return process
    
    def start_esp32_simulator(self, use_laptop_camera: bool = False) -> subprocess.Popen:
        """Start the ESP32-CAM simulator"""
        print("📹 Starting ESP32-CAM Simulator...")
        
        simulator_script = self.base_dir / "esp32_cam_simulator.py"
        
        # Set environment variable for camera choice
        env = os.environ.copy()
        env["ESP32_USE_LAPTOP_CAMERA"] = "true" if use_laptop_camera else "false"
        
        process = subprocess.Popen(
            [sys.executable, str(simulator_script)],
            cwd=str(self.base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env
        )
        
        # Wait for simulator to start
        print("   Waiting for ESP32-CAM simulator to initialize...")
        time.sleep(3)  # Give it more time to start
        
        # Check if process is still running
        if process.poll() is None:
            camera_type = "laptop camera" if use_laptop_camera else "test images"
            print(f"✅ ESP32-CAM Simulator started with {camera_type} (PID: {process.pid})")
            return process
        else:
            print("❌ ESP32-CAM Simulator failed to start")
            return None
    
    def monitor_processes(self):
        """Monitor all running processes"""
        def monitor_loop():
            ai_server_restart_count = 0
            max_ai_server_restarts = 3
            
            while True:
                try:
                    time.sleep(10)
                    
                    # Check process health
                    running_processes = []
                    ai_server_responsive = False
                    
                    for i, (name, process) in enumerate(self.processes):
                        if process and process.poll() is None:
                            running_processes.append(name)
                            
                            # Special check for AI server responsiveness
                            if name == "AI Server":
                                try:
                                    response = requests.get("http://localhost:5001/api/status", timeout=3)
                                    if response.status_code == 200:
                                        ai_server_responsive = True
                                        # Check request count to detect potential memory issues
                                        data = response.json()
                                        request_count = data.get("request_count", 0)
                                        if request_count > 220:
                                            print(f"⚠️ AI Server approaching memory limit (requests: {request_count})")
                                            if request_count > 240:
                                                print(f"🚨 AI Server likely to fail soon - consider restart")
                                    else:
                                        print(f"⚠️ AI Server responding but not healthy (status: {response.status_code})")
                                except:
                                    ai_server_responsive = False
                                    print(f"⚠️ AI Server not responding to health checks")
                        else:
                            print(f"⚠️ Process {name} has stopped")
                            
                            # Auto-restart AI server if it died and we haven't exceeded restart limit
                            if name == "AI Server" and ai_server_restart_count < max_ai_server_restarts:
                                print(f"🔄 Attempting to restart AI Server (attempt {ai_server_restart_count + 1}/{max_ai_server_restarts})")
                                
                                # Remove old process from list
                                self.processes = [(n, p) for n, p in self.processes if n != "AI Server"]
                                
                                # Start new AI server
                                new_ai_server = self.start_ai_server()
                                if new_ai_server:
                                    self.processes.append(("AI Server", new_ai_server))
                                    ai_server_restart_count += 1
                                    print(f"✅ AI Server restarted successfully")
                                else:
                                    print(f"❌ Failed to restart AI Server")
                    
                    if len(running_processes) != len(self.processes):
                        print(f"Running processes: {', '.join(running_processes)}")
                    
                    # Check if AI server is unresponsive (but process still running)
                    ai_server_process_running = any(name == "AI Server" for name, process in self.processes if process and process.poll() is None)
                    if ai_server_process_running and not ai_server_responsive and ai_server_restart_count < max_ai_server_restarts:
                        print(f"🚨 AI Server process running but unresponsive - forcing restart")
                        
                        # Kill unresponsive AI server
                        for name, process in self.processes:
                            if name == "AI Server" and process:
                                try:
                                    process.terminate()
                                    process.wait(timeout=5)
                                except:
                                    try:
                                        process.kill()
                                    except:
                                        pass
                        
                        # Remove from process list
                        self.processes = [(n, p) for n, p in self.processes if n != "AI Server"]
                        
                        # Wait a moment then restart
                        time.sleep(2)
                        new_ai_server = self.start_ai_server()
                        if new_ai_server:
                            self.processes.append(("AI Server", new_ai_server))
                            ai_server_restart_count += 1
                            print(f"✅ Unresponsive AI Server restarted successfully")
                        else:
                            print(f"❌ Failed to restart unresponsive AI Server")
                    
                except Exception as e:
                    print(f"Monitor error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def shutdown_system(self):
        """Shutdown all processes gracefully"""
        print("\n🛑 Shutting down all processes...")
        
        for name, process in self.processes:
            if process and process.poll() is None:
                try:
                    print(f"   Stopping {name}...")
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=5)
                        print(f"   ✅ {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"   🔫 Force killing {name}...")
                        process.kill()
                        process.wait()
                        print(f"   ✅ {name} force stopped")
                        
                except Exception as e:
                    print(f"   ❌ Error stopping {name}: {e}")
        
        self.processes.clear()
        print("✅ All processes stopped")
    
    def display_system_info(self):
        """Display system information and access URLs"""
        print("\n" + "="*60)
        print("🔥🍃 AI DETECTION SYSTEM - RUNNING")
        print("="*60)
        print()
        print("📊 Dashboard:        http://localhost:8080")
        print("🤖 AI Server:        http://localhost:5001")
        print("🤖 AI Server Status: http://localhost:5001/api/status")
        print("📹 ESP32-CAM:        Using laptop camera at 1 FPS")
        print("📱 Camera Preview:   Available in dashboard")
        print()
        print("🚨 AI Detection: Dual-task system")
        print("   🔥 Fire Detection")
        print("   🍃 Yellow Leaves Detection")
        print("⏱️  Frame Rate:     1 FPS (every 1.0 seconds)")
        print("📹 Dashboard Cam:   Start/stop camera preview in web interface")
        print("🔄 Task Switching:  Use toggle buttons in dashboard")
        print()
        print("Press Ctrl+C to stop all services")
        print("="*60)
    
    def launch(self):
        """Launch the complete fire detection system"""
        print("🔥🍃 Complete AI Detection System Launcher")
        print("📹 Dual-task system: Fire + Yellow Leaves Detection")
        print("="*50)
        
        try:
            # Check dependencies
            if not self.check_dependencies():
                print("❌ Dependency check failed")
                return False
            
            # Install packages
            if not self.install_python_packages():
                print("❌ Package installation failed")
                return False
            
            # Always use laptop camera (option 2)
            use_laptop_camera = True
            
            print("\n🚀 Starting system components...")
            
            # Start AI Server
            ai_server = self.start_ai_server()
            if ai_server:
                self.processes.append(("AI Server", ai_server))
            else:
                print("❌ Cannot continue without AI Server")
                return False
            
            # Start Dashboard
            dashboard = self.start_dashboard()
            if dashboard:
                self.processes.append(("Dashboard", dashboard))
            else:
                print("❌ Cannot continue without Dashboard")
                self.shutdown_system()
                return False
            
            # Start ESP32-CAM Simulator with laptop camera
            esp32_sim = self.start_esp32_simulator(use_laptop_camera)
            if esp32_sim:
                self.processes.append(("ESP32-CAM Simulator", esp32_sim))
            else:
                print("⚠️ ESP32-CAM Simulator failed to start, continuing without it")
            
            # Display system information
            self.display_system_info()
            
            # Start monitoring
            self.monitor_processes()
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.shutdown_system()
            print("👋 System shutdown complete!")
            
        except Exception as e:
            print(f"❌ System error: {e}")
            self.shutdown_system()
            return False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Received shutdown signal...")
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and launch system
    system = CompleteFireDetectionSystem()
    system.launch()

if __name__ == "__main__":
    main() 