#include <Wire.h>
#include <DHT20.h>
#include <Adafruit_BMP280.h>
#include <WiFi.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>  // Add JSON library for better parsing

// Cảm biến
DHT20 dht20(&Wire);  // Truyền tham chiếu đối tượng Wire vào
Adafruit_BMP280 bmp;

// Cấu hình chân I2C tùy chỉnh
#define SDA_PIN 11
#define SCL_PIN 12

// Cấu hình chân điều khiển thiết bị
#define LIGHT_PIN 13     // Chân điều khiển đèn
#define FAN_PIN 14       // Chân điều khiển quạt
#define PUMP_PIN 15      // Chân điều khiển bơm

// WiFi credentials
const char* ssid = "PHAM VAN HA";
const char* password = "123456788";

const char* websocketHost = "192.168.1.11"; // Replace with your server's IP
const int websocketPort = 3000;
const char* websocketPath = "/socket.io/?transport=websocket";

WiFiClient wifi;
WebSocketClient webSocketClient(wifi, websocketHost, websocketPort);

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 10000;  // Send data every 10 seconds
unsigned long lastPingTime = 0;
const unsigned long pingInterval = 30000;  // Ping every 30 seconds
bool connected = false;

// Device states
bool lightState = false;
bool fanState = false;
bool pumpState = false;
String currentSector = "A";  // Default sector

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  // Wait for connection
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed");
  }
}


void connectWebSocket() {
  Serial.println("Starting WebSocket connection");
  int result = webSocketClient.begin(websocketPath);
  
  if (result == 0) {
    Serial.println("WebSocket connected!");
    connected = true;
    
    // Send device registration
    webSocketClient.beginMessage(TYPE_TEXT);
    webSocketClient.print("{\"type\":\"device_registration\",\"deviceId\":\"ESP32-Main\",\"sector\":\"" + currentSector + "\"}");
    webSocketClient.endMessage();
  } else {
    Serial.print("WebSocket connection failed with code: ");
    Serial.println(result);
    connected = false;
  }
}


void sendSensorData() {
  // Read DHT20
  float dhtTemp = 0;
  float dhtHum = 0;
  bool dhtSuccess = false;
  
  if (dht20.read() == DHT20_OK) {
    dhtTemp = dht20.getTemperature();
    dhtHum = dht20.getHumidity();
    dhtSuccess = true;
  }
  
  // Read BMP280
  float bmpTemp = bmp.readTemperature();
  float bmpPres = bmp.readPressure() / 100.0F;
  bool bmpSuccess = !isnan(bmpTemp) && !isnan(bmpPres);

  // Fake light sensor value for demo (replace with actual sensor)
  float lightValue = analogRead(A0) / 4095.0 * 1000.0;  // Scale to lux range 0-1000
  
  // Create JSON message with proper structure for server
  DynamicJsonDocument doc(1024);
  doc["type"] = "sensor_data";
  doc["sector"] = currentSector;
  
  if (dhtSuccess) {
    doc["temperature"] = dhtTemp;
    doc["humidity"] = dhtHum;
  }
  
  if (bmpSuccess) {
    // Use BMP temp as backup if DHT fails
    if (!dhtSuccess) {
      doc["temperature"] = bmpTemp;
    }
    doc["pressure"] = bmpPres;
  }
  
  doc["light"] = lightValue;
  
  // Also send current device states
  JsonObject devices = doc.createNestedObject("devices");
  devices["Light"] = lightState;
  devices["Motor Fan"] = fanState;
  devices["Pump"] = pumpState;
  
  String message;
  serializeJson(doc, message);
  
  // Send data over WebSocket
  if (connected) {
    webSocketClient.beginMessage(TYPE_TEXT);
    webSocketClient.print(message);
    webSocketClient.endMessage();
    Serial.println("Sent: " + message);
  }
}

void processCommand(String command) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, command);
  
  if (error) {
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Check if this is a command message
  if (doc.containsKey("type") && doc["type"] == "device_command") {
    String sector = doc["sector"];
    String device = doc["device"];
    bool status = doc["status"];
    String controlType = doc["type"];
    
    Serial.print("Received command for device: ");
    Serial.print(device);
    Serial.print(" in sector: ");
    Serial.print(sector);
    Serial.print(" - Status: ");
    Serial.print(status ? "ON" : "OFF");
    Serial.print(" - Type: ");
    Serial.println(controlType);
    
    // Update the current sector if it's different
    if (sector != currentSector) {
      currentSector = sector;
      Serial.print("Sector changed to: ");
      Serial.println(currentSector);
    }
    
    // Handle device commands
    if (device == "Light") {
      lightState = status;
      digitalWrite(LIGHT_PIN, lightState ? HIGH : LOW);
      Serial.println(lightState ? "Light turned ON" : "Light turned OFF");
    }
    else if (device == "Motor Fan") {
      fanState = status;
      digitalWrite(FAN_PIN, fanState ? HIGH : LOW);
      Serial.println(fanState ? "Fan turned ON" : "Fan turned OFF");
    }
    else if (device == "Pump") {
      pumpState = status;
      digitalWrite(PUMP_PIN, pumpState ? HIGH : LOW);
      Serial.println(pumpState ? "Pump turned ON" : "Pump turned OFF");
    }
    
    // Send acknowledgment
    DynamicJsonDocument ackDoc(256);
    ackDoc["type"] = "command_ack";
    ackDoc["device"] = device;
    ackDoc["status"] = status;
    ackDoc["success"] = true;
    
    String ackMessage;
    serializeJson(ackDoc, ackMessage);
    
    webSocketClient.beginMessage(TYPE_TEXT);
    webSocketClient.print(ackMessage);
    webSocketClient.endMessage();
  }
}

void receiveMessages() {
  int messageSize = webSocketClient.parseMessage();
  
  if (messageSize > 0) {
    Serial.print("Received WebSocket message: ");
    String message = webSocketClient.readString();
    Serial.println(message);
    
    // Process the received message
    processCommand(message);
  }
}

bool pingServer() {
  if (!connected) {
    Serial.println("Not connected to WebSocket server. Cannot ping.");
    return false;
  }
  
  Serial.println("Pinging WebSocket server...");
  
  // Send a ping message
  webSocketClient.beginMessage(TYPE_TEXT);
  webSocketClient.print("{\"type\":\"ping\"}");
  webSocketClient.endMessage();
  
  // Wait briefly for a response
  unsigned long pingStart = millis();
  bool receivedResponse = false;
  
  // Check for response with timeout
  while (millis() - pingStart < 3000) {
    int messageSize = webSocketClient.parseMessage();
    
    if (messageSize > 0) {
      String response = webSocketClient.readString();
      Serial.println("Received response: " + response);
      receivedResponse = true;
      break;
    }
    delay(50);
  }
  
  if (receivedResponse) {
    Serial.println("Ping successful!");
    return true;
  } else {
    Serial.println("Ping timeout - no response from server");
    connected = false;
    return false;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Configure device control pins
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  
  // Initialize all devices to OFF
  digitalWrite(LIGHT_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(PUMP_PIN, LOW);

  // Khởi động I2C với chân tùy chỉnh
  Wire.begin(SDA_PIN, SCL_PIN);
  Serial.println("Đã khởi động I2C.");

  // Khởi động DHT20
  if (!dht20.begin()) {
    Serial.println("Không tìm thấy DHT20!");
  } else {
    Serial.println("Đã kết nối DHT20.");
  }

  // Khởi động BMP280
  if (!bmp.begin(0x76)) {
    Serial.println("Không tìm thấy BMP280!");
  } else {
    Serial.println("Đã kết nối BMP280.");
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
  }
  connectWiFi();
}

void loop() {
  unsigned long currentMillis = millis();

  if (WiFi.status() != WL_CONNECTED) {
    connected = false;
    Serial.println("WiFi disconnected, reconnecting...");
    connectWiFi();
    return;
  }

  if (!connected) {
    connectWebSocket();
    delay(1000);
    
    // Test the connection with a ping
    if (connected) {
      bool pingSuccess = pingServer();
      if (!pingSuccess) {
        Serial.println("Ping failed, socket may not be working properly");
      }
    }
  } else {
    // Check for incoming messages
    receiveMessages();
    
    // Send sensor data on interval
    if (currentMillis - lastSendTime >= sendInterval) {
      lastSendTime = currentMillis;
      sendSensorData();
    }
    
    // Periodically ping to verify connection is still alive
    if (currentMillis - lastPingTime >= pingInterval) {
      lastPingTime = currentMillis;
      pingServer();
    }
  }
}
