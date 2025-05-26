#include <Wire.h>
#include <DHT20.h>
#include <Adafruit_BMP280.h>
#include <WiFi.h>
#include <ArduinoHttpClient.h>

// Cảm biến
DHT20 dht20(&Wire);  // Truyền tham chiếu đối tượng Wire vào
Adafruit_BMP280 bmp;

// Cấu hình chân I2C tùy chỉnh
#define SDA_PIN 11
#define SCL_PIN 12

// WiFi credentials
const char* ssid = "PHAM VAN HA";
const char* password = "123456788";

const char* websocketHost = "192.168.1.11"; // Replace with your computer's IP
const int websocketPort = 3000;
const char* websocketPath = "/socket.io/?transport=websocket";


WiFiClient wifi;
WebSocketClient webSocketClient(wifi, websocketHost, websocketPort);



bool connected = false;

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
    
    // Send a ping message
    webSocketClient.beginMessage(TYPE_TEXT);
    webSocketClient.print("{\"type\":\"ping\"}");
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
  
  // Create JSON message
  String message = "{\"data\":{";
  
  if (dhtSuccess) {
    message += "\"dht20\":{\"temperature\":" + String(dhtTemp) + 
              ",\"humidity\":" + String(dhtHum) + "}";
    if (bmpSuccess) message += ",";
  }
  
  if (bmpSuccess) {
    message += "\"bmp280\":{\"temperature\":" + String(bmpTemp) + 
              ",\"pressure\":" + String(bmpPres) + "}";
  }
  
  message += "}}";
  
  // Send data over WebSocket
  if (connected) {
    webSocketClient.beginMessage(TYPE_TEXT);
    webSocketClient.print(message);
    webSocketClient.endMessage();
    Serial.println("Sent: " + message);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

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


void receiveMessages() {
  int messageSize = webSocketClient.parseMessage();
  
  if (messageSize > 0) {
    Serial.print("Received WebSocket message: ");
    String message = webSocketClient.readString();
    Serial.println(message);
    
    // Here you could parse and handle commands from the server
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

void loop() {
  Serial.println("----- Đọc dữ liệu -----");

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
    // Periodically ping to verify connection is still alive
    static unsigned long lastPingTime = 0;
    if (millis() - lastPingTime > 30000) { // Ping every 30 seconds
      lastPingTime = millis();
      pingServer();
    }
  }

  // unsigned long currentMillis = millis();
  // if (currentMillis - lastSendTime >= sendInterval) {
  //   lastSendTime = currentMillis;
  //   sendSensorData();
  // }

  // Đọc DHT20
  if (dht20.read() == DHT20_OK) {
    float dhtTemp = dht20.getTemperature();
    float dhtHum  = dht20.getHumidity();
    Serial.print("[DHT20] Nhiệt độ: "); Serial.print(dhtTemp); Serial.println(" °C");
    Serial.print("[DHT20] Độ ẩm:    "); Serial.print(dhtHum); Serial.println(" %");
  } else {
    Serial.println("[DHT20] Lỗi đọc dữ liệu!");
  }

  // Đọc BMP280
  float bmpTemp = bmp.readTemperature();
  float bmpPres = bmp.readPressure() / 100.0F;

  if (isnan(bmpTemp) || isnan(bmpPres)) {
    Serial.println("[BMP280] Lỗi đọc dữ liệu!");
  } else {
    Serial.print("[BMP280] Nhiệt độ: "); Serial.print(bmpTemp); Serial.println(" °C");
    Serial.print("[BMP280] Áp suất:  "); Serial.print(bmpPres); Serial.println(" hPa");
  }

  Serial.println("------------------------\n");
  delay(3000);
}
