/**
 * ESP32-CAM Hybrid AI Processing
 * Captures images locally and sends to server for AI inference
 * 
 * This approach is recommended for:
 * - Complex models (YOLO, etc.) that don't fit on ESP32
 * - High-resolution image processing
 * - Multiple model processing
 * - Better accuracy requirements
 * 
 * Architecture:
 * ESP32-CAM → Capture Image → Send to Server → AI Processing → Results back to ESP32
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <base64.h>
#include "esp_camera.h"

// Camera pin configuration for AI Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// WiFi Configuration
#define WIFI_SSID "YOUR_WIFI_SSID"     // ⚠️ CHANGE THIS to your WiFi name
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"  // ⚠️ CHANGE THIS to your WiFi password

// Server Configuration
#define AI_SERVER_URL "http://192.168.15.4:5001/api/detect"  // ✅ Updated with your Mac's IP and correct port
#define SERVER_TIMEOUT 10000  // 10 seconds timeout

// MQTT Configuration
#define MQTT_BROKER "app.coreiot.io"
#define MQTT_PORT 1883
#define MQTT_USER "iot_farm"
#define MQTT_PASSWORD "123456789"
#define MQTT_DETECTION_TOPIC "coreiot/device123/ai_detections"

// Detection Settings
#define CAPTURE_INTERVAL 5000     // Capture every 5 seconds
#define DETECTION_THRESHOLD 0.7   // Confidence threshold
#define MAX_IMAGE_SIZE 100000     // Maximum image size in bytes

WiFiClient espClient;
PubSubClient mqttClient(espClient);
HTTPClient http;

unsigned long lastCaptureTime = 0;
bool isDetectionEnabled = true;

/**
 * Initialize camera with optimal settings
 */
bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    
    // Higher resolution for better AI accuracy
    config.frame_size = FRAMESIZE_VGA;  // 640x480
    config.jpeg_quality = 12;           // Lower number = higher quality
    config.fb_count = 1;
    
    // Initialize camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return false;
    }
    
    // Get camera sensor and adjust settings
    sensor_t* s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_brightness(s, 0);     // -2 to 2
        s->set_contrast(s, 0);       // -2 to 2
        s->set_saturation(s, 0);     // -2 to 2
        s->set_special_effect(s, 0); // 0 to 6 (0-No Effect, 1-Negative, 2-Grayscale...)
        s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
        s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
        s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
        s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
        s->set_aec2(s, 0);           // 0 = disable , 1 = enable
        s->set_ae_level(s, 0);       // -2 to 2
        s->set_aec_value(s, 300);    // 0 to 1200
        s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
        s->set_agc_gain(s, 0);       // 0 to 30
        s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
        s->set_bpc(s, 0);            // 0 = disable , 1 = enable
        s->set_wpc(s, 1);            // 0 = disable , 1 = enable
        s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
        s->set_lenc(s, 1);           // 0 = disable , 1 = enable
        s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
        s->set_vflip(s, 0);          // 0 = disable , 1 = enable
        s->set_dcw(s, 1);            // 0 = disable , 1 = enable
        s->set_colorbar(s, 0);       // 0 = disable , 1 = enable
    }
    
    Serial.println("Camera initialized successfully");
    return true;
}

/**
 * Connect to WiFi network
 */
void connectToWiFi() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi");
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println();
    Serial.printf("Connected! IP: %s\n", WiFi.localIP().toString().c_str());
}

/**
 * Connect to MQTT broker
 */
void connectToMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Connecting to MQTT...");
        
        if (mqttClient.connect("ESP32CAM_Hybrid_AI", MQTT_USER, MQTT_PASSWORD)) {
            Serial.println("Connected!");
            mqttClient.subscribe("coreiot/device123/commands");
        } else {
            Serial.printf("Failed, rc=%d. Retrying in 5s...\n", mqttClient.state());
            delay(5000);
        }
    }
}

/**
 * MQTT callback for commands
 */
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.printf("MQTT Command: %s\n", message.c_str());
    
    if (message == "enable_detection") {
        isDetectionEnabled = true;
    } else if (message == "disable_detection") {
        isDetectionEnabled = false;
    } else if (message == "capture_now") {
        // Force immediate capture
        lastCaptureTime = 0;
    }
}

/**
 * Capture image and convert to base64
 */
String captureImageBase64() {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        return "";
    }
    
    // Check image size
    if (fb->len > MAX_IMAGE_SIZE) {
        Serial.printf("Image too large: %d bytes\n", fb->len);
        esp_camera_fb_return(fb);
        return "";
    }
    
    // Convert to base64
    String base64Image = base64::encode(fb->buf, fb->len);
    
    esp_camera_fb_return(fb);
    return base64Image;
}

/**
 * Send image to AI server for processing
 */
JsonDocument sendImageForProcessing(const String& base64Image) {
    JsonDocument response;
    
    if (WiFi.status() != WL_CONNECTED) {
        response["error"] = "WiFi not connected";
        return response;
    }
    
    http.begin(AI_SERVER_URL);
    http.setTimeout(SERVER_TIMEOUT);
    http.addHeader("Content-Type", "application/json");
    
    // Prepare request payload
    JsonDocument request;
    request["image"] = base64Image;
    request["model"] = "fire_detection_best";  // Specify which model to use
    request["threshold"] = DETECTION_THRESHOLD;
    request["device_id"] = "ESP32CAM_001";
    request["timestamp"] = millis();
    
    String requestString;
    serializeJson(request, requestString);
    
    Serial.println("Sending image to AI server...");
    int httpResponseCode = http.POST(requestString);
    
    if (httpResponseCode == 200) {
        String responseString = http.getString();
        deserializeJson(response, responseString);
        Serial.printf("AI Server Response: %s\n", responseString.c_str());
    } else {
        Serial.printf("HTTP Error: %d\n", httpResponseCode);
        response["error"] = "HTTP Error: " + String(httpResponseCode);
    }
    
    http.end();
    return response;
}

/**
 * Process AI detection results
 */
void processDetectionResults(const JsonDocument& results) {
    if (results.containsKey("error")) {
        Serial.printf("AI Processing Error: %s\n", results["error"].as<const char*>());
        return;
    }
    
    if (!results.containsKey("detections")) {
        Serial.println("No detections in response");
        return;
    }
    
    JsonArray detections = results["detections"];
    int detectionCount = detections.size();
    
    Serial.printf("Received %d detection(s)\n", detectionCount);
    
    if (detectionCount > 0) {
        // Process each detection
        for (JsonVariant detection : detections) {
            String objectClass = detection["class"];
            float confidence = detection["confidence"];
            
            Serial.printf("Detected: %s (%.2f confidence)\n", 
                          objectClass.c_str(), confidence);
            
            // Publish significant detections
            if (confidence >= DETECTION_THRESHOLD) {
                publishDetectionAlert(objectClass, confidence, results);
            }
        }
    }
}

/**
 * Publish detection alert via MQTT
 */
void publishDetectionAlert(const String& objectClass, float confidence, const JsonDocument& fullResults) {
    JsonDocument alert;
    
    alert["device_id"] = "ESP32CAM_Hybrid_001";
    alert["timestamp"] = millis();
    alert["detection"]["class"] = objectClass;
    alert["detection"]["confidence"] = confidence;
    alert["detection"]["method"] = "server_processing";
    
    // Special handling for fire detection
    if (objectClass == "fire") {
        alert["alert"]["type"] = "FIRE_DETECTED";
        alert["alert"]["severity"] = "CRITICAL";
        alert["alert"]["action_required"] = true;
        alert["alert"]["recommended_action"] = "Immediate evacuation and fire suppression";
    }
    
    // Include processing time
    if (fullResults.containsKey("processing_time_ms")) {
        alert["processing"]["server_time_ms"] = fullResults["processing_time_ms"];
    }
    
    char alertBuffer[1024];
    serializeJson(alert, alertBuffer);
    
    mqttClient.publish(MQTT_DETECTION_TOPIC, alertBuffer);
    Serial.printf("Published alert: %s\n", alertBuffer);
}

/**
 * Main AI processing task
 */
void TaskHybridAI(void *pvParameters) {
    Serial.println("Hybrid AI processing task started");
    
    while (1) {
        // Ensure connections
        if (!mqttClient.connected()) {
            connectToMQTT();
        }
        mqttClient.loop();
        
        // Check if it's time to capture
        unsigned long currentTime = millis();
        if (isDetectionEnabled && (currentTime - lastCaptureTime >= CAPTURE_INTERVAL)) {
            
            Serial.println("Capturing image for AI processing...");
            
            // Capture image
            String base64Image = captureImageBase64();
            if (base64Image.length() > 0) {
                
                // Send to server for processing
                JsonDocument results = sendImageForProcessing(base64Image);
                
                // Process results
                processDetectionResults(results);
                
                lastCaptureTime = currentTime;
            }
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));  // Check every second
    }
}

void setup() {
    Serial.begin(115200);
    delay(3000);
    
    Serial.println("=== ESP32-CAM Hybrid AI Processing ===");
    
    // Initialize camera
    if (!initCamera()) {
        Serial.println("Camera initialization failed!");
        ESP.restart();
    }
    
    // Connect to WiFi
    connectToWiFi();
    
    // Setup MQTT
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    
    // Create hybrid AI task
    xTaskCreatePinnedToCore(
        TaskHybridAI,       // Task function
        "Hybrid_AI",        // Task name
        8192,              // Stack size
        NULL,              // Parameters
        2,                 // Priority
        NULL,              // Task handle
        1                  // Core 1
    );
    
    Serial.println("Setup complete. Hybrid AI processing active.");
    Serial.printf("AI Server: %s\n", AI_SERVER_URL);
    Serial.printf("Capture Interval: %d ms\n", CAPTURE_INTERVAL);
    Serial.printf("Detection Threshold: %.2f\n", DETECTION_THRESHOLD);
}

void loop() {
    // Main loop handles other tasks
    delay(1000);
}

/**
 * Example server endpoint implementation (Python Flask):
 * 
 * @app.route('/api/detect', methods=['POST'])
 * def detect_objects():
 *     data = request.get_json()
 *     
 *     # Decode base64 image
 *     image_data = base64.b64decode(data['image'])
 *     
 *     # Load YOLO model and run inference
 *     results = yolo_model.predict(image_data)
 *     
 *     detections = []
 *     for result in results:
 *         detections.append({
 *             'class': result.class_name,
 *             'confidence': result.confidence,
 *             'bbox': result.bbox
 *         })
 *     
 *     return jsonify({
 *         'detections': detections,
 *         'processing_time_ms': processing_time,
 *         'model_version': 'yolov8m_fire_detection'
 *     })
 */ 