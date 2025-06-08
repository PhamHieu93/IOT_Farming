#include <Arduino.h>
#include <DHT20.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Pin Definitions
#define LED_PIN         GPIO_NUM_48
#define LIGHT_SENSOR_PIN GPIO_NUM_2
#define DHT_SDA_PIN     GPIO_NUM_11
#define DHT_SCL_PIN     GPIO_NUM_12

// WiFi Configuration
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// MQTT Configuration (CoreIoT Cloud)
#define MQTT_BROKER "app.coreiot.io"  // CoreIoT broker address
#define MQTT_PORT 1883                   // Typically 8883 for SSL
#define MQTT_USER "iot_farm"      // CoreIoT credentials
#define MQTT_PASSWORD "123456789" // CoreIoT credentials
#define MQTT_PUB_TOPIC "coreiot/device123/sensor_data"
#define MQTT_SUB_TOPIC "coreiot/device123/commands"

WiFiClient espClient;
PubSubClient mqttClient(espClient);
DHT20 dht20;

void connectToWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP());
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message received [");
  Serial.print(topic);
  Serial.print("]: ");
  
  // Handle incoming commands
  String message;
  for (int i=0; i<length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
}

void connectToMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");
    
    if (mqttClient.connect("ESP32_Client", MQTT_USER, MQTT_PASSWORD)) {
      Serial.println("Connected!");
      mqttClient.subscribe(MQTT_SUB_TOPIC);
    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retrying in 5s...");
      delay(5000);
    }
  }
}

void publishSensorData(float temp, float humi, int light) {
  StaticJsonDocument<200> doc;
  doc["temperature"] = temp;
  doc["humidity"] = humi;
  doc["light"] = light;
  
  doc["timestamp"] = millis();

  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  mqttClient.publish(MQTT_PUB_TOPIC, jsonBuffer);
}

void TaskSensorMQTT(void *pvParameters) {
  Wire.begin(DHT_SDA_PIN, DHT_SCL_PIN);
  dht20.begin();
  pinMode(LIGHT_SENSOR_PIN, INPUT);

  while(1) {
    // Ensure MQTT connection
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    mqttClient.loop();

    // Read sensors
    dht20.read();
    float temperature = dht20.getTemperature();
    float humidity = dht20.getHumidity();
    int lightValue = analogRead(LIGHT_SENSOR_PIN);

    // Publish data
    publishSensorData(temperature, humidity, lightValue);
    
    vTaskDelay(pdMS_TO_TICKS(10000)); // 10-second interval
  }
}

void setup() {
  Serial.begin(115200);
  connectToWiFi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  
  xTaskCreate(TaskSensorMQTT, "Sensor/MQTT", 4096, NULL, 2, NULL);
}

void loop() {}