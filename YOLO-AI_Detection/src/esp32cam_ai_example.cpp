/**
 * ESP32-CAM AI Object Detection Integration
 * Uses Edge Impulse FOMO model for lightweight object detection
 * 
 * This example demonstrates how to:
 * 1. Capture images from ESP32-CAM
 * 2. Run inference using a lightweight AI model
 * 3. Send detection results via MQTT
 * 
 * Hardware Requirements:
 * - ESP32-CAM module (AI Thinker or similar)
 * - External antenna recommended for better WiFi
 * 
 * Software Requirements:
 * - Edge Impulse trained FOMO model (exported as Arduino library)
 * - EloquentEsp32Cam library
 * 
 * Setup Instructions:
 * 1. Train a FOMO model on Edge Impulse (48x48 or 96x96 resolution)
 * 2. Export as Arduino library and add to lib_deps
 * 3. Configure WiFi and MQTT settings
 * 4. Upload and test
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <eloquent_esp32cam.h>
#include <eloquent_esp32cam/edgeimpulse/fomo.h>

// Include your Edge Impulse model header
// #include <your_fire_detection_model_inferencing.h>

using eloq::camera;
using eloq::ei::fomo;

// WiFi Configuration
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// MQTT Configuration
#define MQTT_BROKER "app.coreiot.io"
#define MQTT_PORT 1883
#define MQTT_USER "iot_farm"
#define MQTT_PASSWORD "123456789"
#define MQTT_DETECTION_TOPIC "coreiot/device123/ai_detections"

// Detection Settings
#define DETECTION_THRESHOLD 0.7  // Confidence threshold
#define DETECTION_INTERVAL 2000  // Detection interval in ms

WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastDetectionTime = 0;
bool isDetectionEnabled = true;

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
 * MQTT callback for receiving commands
 */
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.printf("MQTT Message [%s]: %s\n", topic, message.c_str());
    
    // Handle commands
    if (message == "enable_detection") {
        isDetectionEnabled = true;
        Serial.println("AI Detection enabled");
    } else if (message == "disable_detection") {
        isDetectionEnabled = false;
        Serial.println("AI Detection disabled");
    }
}

/**
 * Connect to MQTT broker
 */
void connectToMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Connecting to MQTT...");
        
        if (mqttClient.connect("ESP32CAM_AI_Client", MQTT_USER, MQTT_PASSWORD)) {
            Serial.println("Connected!");
            mqttClient.subscribe("coreiot/device123/commands");
        } else {
            Serial.printf("Failed, rc=%d. Retrying in 5s...\n", mqttClient.state());
            delay(5000);
        }
    }
}

/**
 * Publish AI detection results to MQTT
 */
void publishDetectionResults(int objectCount, const char* primaryObject, float confidence) {
    StaticJsonDocument<512> doc;
    
    doc["device_id"] = "ESP32CAM_AI_001";
    doc["timestamp"] = millis();
    doc["detection"]["objects_detected"] = objectCount;
    doc["detection"]["primary_object"] = primaryObject;
    doc["detection"]["confidence"] = confidence;
    doc["detection"]["threshold"] = DETECTION_THRESHOLD;
    
    // Add alert status for fire detection
    if (strcmp(primaryObject, "fire") == 0 && confidence > DETECTION_THRESHOLD) {
        doc["alert"]["type"] = "FIRE_DETECTED";
        doc["alert"]["severity"] = "HIGH";
        doc["alert"]["action_required"] = true;
    }
    
    char jsonBuffer[512];
    serializeJson(doc, jsonBuffer);
    
    mqttClient.publish(MQTT_DETECTION_TOPIC, jsonBuffer);
    Serial.printf("Published detection: %s\n", jsonBuffer);
}

/**
 * Initialize camera with optimal settings for AI inference
 */
void initializeCamera() {
    Serial.println("Initializing ESP32-CAM...");
    
    // Camera settings for AI inference
    camera.pinout.aithinker();  // Use appropriate pinout for your board
    camera.brownout.disable();
    
    // Use grayscale for better performance and smaller model size
    camera.resolution.yolo();   // 96x96 resolution for FOMO
    camera.pixformat.grayscale();  // Grayscale for smaller model
    camera.quality.high();
    
    // Initialize camera
    while (!camera.begin().isOk()) {
        Serial.printf("Camera init error: %s\n", camera.exception.toString());
        delay(1000);
    }
    
    Serial.println("Camera initialized successfully!");
}

/**
 * Run AI inference on captured image
 */
void runAIDetection() {
    if (!isDetectionEnabled) {
        return;
    }
    
    unsigned long currentTime = millis();
    if (currentTime - lastDetectionTime < DETECTION_INTERVAL) {
        return;
    }
    
    // Capture image
    if (!camera.capture().isOk()) {
        Serial.printf("Capture error: %s\n", camera.exception.toString());
        return;
    }
    
    // Run FOMO inference
    if (!fomo.run().isOk()) {
        Serial.printf("Inference error: %s\n", fomo.exception.toString());
        return;
    }
    
    int objectCount = fomo.count();
    Serial.printf("Found %d object(s) in %dms\n", objectCount, fomo.benchmark.millis());
    
    if (objectCount > 0) {
        // Get the first (most confident) detection
        auto firstDetection = fomo.first;
        
        Serial.printf("Detected: %s at (%d, %d) with confidence %.2f\n",
                      firstDetection.label,
                      firstDetection.x,
                      firstDetection.y,
                      firstDetection.proba);
        
        // Publish results if confidence exceeds threshold
        if (firstDetection.proba >= DETECTION_THRESHOLD) {
            publishDetectionResults(objectCount, firstDetection.label, firstDetection.proba);
        }
        
        // Print all detections for debugging
        fomo.forEach([](int i, bbox_t bbox) {
            Serial.printf("#%d) %s at (%d, %d) [%dx%d] confidence: %.2f\n",
                          i + 1, bbox.label, bbox.x, bbox.y,
                          bbox.width, bbox.height, bbox.proba);
        });
    }
    
    lastDetectionTime = currentTime;
}

/**
 * AI Detection task running on separate core
 */
void TaskAIDetection(void *pvParameters) {
    Serial.println("AI Detection task started");
    
    while (1) {
        // Ensure MQTT connection
        if (!mqttClient.connected()) {
            connectToMQTT();
        }
        mqttClient.loop();
        
        // Run AI detection
        runAIDetection();
        
        // Small delay to prevent watchdog trigger
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void setup() {
    Serial.begin(115200);
    delay(3000);  // Allow serial monitor to connect
    
    Serial.println("=== ESP32-CAM AI Object Detection ===");
    
    // Initialize camera
    initializeCamera();
    
    // Connect to WiFi
    connectToWiFi();
    
    // Setup MQTT
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    
    // Create AI detection task on Core 0
    xTaskCreatePinnedToCore(
        TaskAIDetection,    // Task function
        "AI_Detection",     // Task name
        8192,              // Stack size
        NULL,              // Parameters
        2,                 // Priority
        NULL,              // Task handle
        0                  // Core (0 for AI processing)
    );
    
    Serial.println("Setup complete. AI detection active.");
}

void loop() {
    // Main loop can handle other tasks
    // AI detection runs on separate task
    delay(1000);
}

/**
 * Alternative approach for hybrid processing:
 * Send images to external server for processing
 */
void setupHybridProcessing() {
    // This function demonstrates how to send images to
    // a more powerful server for AI processing
    
    // 1. Capture high-resolution image
    // 2. Compress and send to server via HTTP POST
    // 3. Receive detection results
    // 4. Take action based on results
    
    // Example HTTP endpoint:
    // POST /api/detect with image data
    // Response: {"detections": [{"class": "fire", "confidence": 0.85}]}
} 