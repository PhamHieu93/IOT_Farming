#define LED_PIN 48
#define SDA_PIN GPIO_NUM_11
#define SCL_PIN GPIO_NUM_12
#define LIGHT_SENSOR_PIN GPIO_NUM_1
#define MOISTURE_PIN GPIO_NUM_2



#include <WiFi.h>
#include <Arduino_MQTT_Client.h>
#include <ThingsBoard.h>
#include "DHT20.h"
#include "Wire.h"
#include <ArduinoOTA.h>
#include <ArduinoJson.h>

constexpr char WIFI_SSID[] = "Hiuu";
constexpr char WIFI_PASSWORD[] = "phamhiu93";

constexpr char TOKEN[] = "ttrv0asoe3tln5zqjswc";

constexpr char THINGSBOARD_SERVER[] = "app.coreiot.io";
constexpr uint16_t THINGSBOARD_PORT = 1883U;

constexpr uint32_t MAX_MESSAGE_SIZE = 1024U;
constexpr uint32_t SERIAL_DEBUG_BAUD = 115200U;

constexpr char BLINKING_INTERVAL_ATTR[] = "blinkingInterval";
constexpr char LED_MODE_ATTR[] = "ledMode";
constexpr char LED_STATE_ATTR[] = "ledState";

volatile bool attributesChanged = false;
volatile int ledMode = 0;
volatile bool ledState = false;

constexpr uint16_t BLINKING_INTERVAL_MS_MIN = 10U;
constexpr uint16_t BLINKING_INTERVAL_MS_MAX = 60000U;
volatile uint16_t blinkingInterval = 1000U;

uint32_t previousStateChange;

constexpr int16_t telemetrySendInterval = 10000U;
uint32_t previousDataSend;

constexpr std::array<const char *, 2U> SHARED_ATTRIBUTES_LIST = {
  LED_STATE_ATTR,
  BLINKING_INTERVAL_ATTR
};

WiFiClient wifiClient;
Arduino_MQTT_Client mqttClient(wifiClient);
ThingsBoard tb(mqttClient, MAX_MESSAGE_SIZE);

DHT20 dht20;


const double long_HCMUT = 106.65789107082472;
const double lat_HCMUT = 10.772175109674038;
float temperature = 0.0f, humidity = 0.0f;
float light = 0.0f, moisture = 0.0f;

// Forward declaration tasks
void taskThingsBoard(void *parameter);
void taskDHT20(void *parameter);
// void taskLight(void *parameter);
void taskSerial(void *parameter);
// void taskPrintVersion(void *parameter);
void taskSerialCommand(void *parameter);

// Khai báo TaskHandle_t
TaskHandle_t taskDHT20Handle = NULL;
TaskHandle_t taskSendTelemetryHandle = NULL;
TaskHandle_t taskLightHandle = NULL;
TaskHandle_t taskSerialHandle = NULL;


RPC_Response setLedSwitchState(const RPC_Data &data) {
    Serial.println("Received Switch state");
    bool newState = data;
    Serial.print("Switch state change: ");
    Serial.println(newState);
    digitalWrite(LED_PIN, newState);
    ledState = newState;
    attributesChanged = true;
    return RPC_Response("setValue", newState);
}

const std::array<RPC_Callback, 1U> callbacks = {
  RPC_Callback{ "setValue", setLedSwitchState }
};

void processSharedAttributes(const JsonObjectConst &data) {
    Serial.println("[TB] Received shared attributes:");
    for (auto it = data.begin(); it != data.end(); ++it) {
        Serial.printf("  Key: %s, Value: ", it->key().c_str());
        if (it->value().is<const char*>()) Serial.println(it->value().as<const char*>());
        else if (it->value().is<int>()) Serial.println(it->value().as<int>());
        else if (it->value().is<float>()) Serial.println(it->value().as<float>());
        else {
            serializeJson(it->value(), Serial);
            Serial.println();
        }
    }
}

const Shared_Attribute_Callback attributes_callback(&processSharedAttributes, SHARED_ATTRIBUTES_LIST.cbegin(), SHARED_ATTRIBUTES_LIST.cend());
const Attribute_Request_Callback attribute_shared_request_callback(&processSharedAttributes, SHARED_ATTRIBUTES_LIST.cbegin(), SHARED_ATTRIBUTES_LIST.cend());

void InitWiFi() {
  Serial.println("Connecting to AP ...");
  // Attempting to establish a connection to the given WiFi network
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    // Delay 500ms until a connection has been successfully established
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to AP");
}

const bool reconnect() {
  // Check to ensure we aren't connected yet
  const wl_status_t status = WiFi.status();
  if (status == WL_CONNECTED) {
    return true;
  }
  // If we aren't establish a new connection to the given WiFi network
  InitWiFi();
  return true;
}

void processGetJson(const JsonVariantConst &data, JsonDocument &response) {
//   Serial.println("Received the json RPC method");

  // Size of the response document needs to be configured to the size of the innerDoc + 1.
  StaticJsonDocument<JSON_OBJECT_SIZE(128)> innerDoc;
  innerDoc["string"] = "exampleResponseString";
  innerDoc["int"] = 5;
  innerDoc["float"] = 5.0f;
  innerDoc["bool"] = true;
  response["json_data"] = innerDoc;
}

void processSerialCommand() {
  if (Serial.available()) {
    String jsonString = Serial.readStringUntil('\n');
    Serial.print("Received JSON: ");
    Serial.println(jsonString);
    
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }

    if (doc.containsKey("switch")) {
      bool newState = doc["switch"];
      digitalWrite(LED_PIN, newState);
      ledState = newState;
      Serial.print("LED state changed to: ");
      Serial.println(newState);
      Serial.print("LED PIN state: ");
      Serial.println(digitalRead(LED_PIN));
      attributesChanged = true;
    }
  }
}

void processSwitchChange(const JsonVariantConst &data, JsonDocument &response) {
//   Serial.println("Received the set switch method");

  // Process data
  const bool switch_state = data.as<bool>();

//   Serial.print("Example switch state: ");
//   Serial.println(switch_state);

  if (switch_state) {
    Serial.println("Switch is ON");
    digitalWrite(LED_PIN, HIGH);
  } else {
    Serial.println("Switch is OFF");
    digitalWrite(LED_PIN, LOW);
  }

  response.set(switch_state);
}

void setup() {
  Serial.begin(SERIAL_DEBUG_BAUD);
  Serial.println("\n\n--- ESP32 Sensor System Starting ---");
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);  
  pinMode(MOISTURE_PIN, INPUT);  
  
  // Turn on LED initially
  digitalWrite(LED_PIN, HIGH);
  ledState = true;
  
  delay(1000);
  Serial.println("Initializing WiFi...");
  InitWiFi();

  Serial.println("Initializing I2C...");
  Wire.begin(SDA_PIN, SCL_PIN);
  dht20.begin();
  Serial.println("DHT20 initialized");

  Serial.println("Creating tasks...");
  xTaskCreate(taskThingsBoard, "TaskThingsBoard", 4096, NULL, 1, NULL);
  xTaskCreate(taskSerialCommand, "TaskSerialCommand", 2048, NULL, 1, NULL);
  xTaskCreate(taskDHT20, "TaskDHT20", 4096, NULL, 1, &taskDHT20Handle);
  // xTaskCreate(taskLight, "TaskLight", 4096, NULL, 1, &taskLightHandle);
  xTaskCreate(taskSerial, "TaskSerial", 4096, NULL, 1, &taskSerialHandle);
  // xTaskCreate(taskPrintVersion, "TaskPrintVersion", 2048, NULL, 1, NULL);
  
  Serial.println("Setup complete!");
}


void taskSerial(void *parameter){
    while(1){
      Serial.print("Temperature: ");
      Serial.print(temperature);
      Serial.print(" °C, Humidity: ");
      Serial.print(humidity);
      Serial.print(" %,  Light: ");
      Serial.print(light);  // Print raw analog value
      Serial.print(" Moisture: ");
      Serial.print(moisture);  // Print raw analog value
      Serial.println(" %");
      vTaskDelay(1000 / portTICK_PERIOD_MS);

      tb.sendTelemetryData("temperature", temperature);
      tb.sendTelemetryData("humidity", humidity);
      tb.sendTelemetryData("light", light);
      tb.sendTelemetryData("moisture", moisture); 
    }
}

void taskSerialCommand(void *parameter) {
    StaticJsonDocument<64> doc;
    String input;
    while (1) {
        while (Serial.available()) {
            char c = Serial.read();
            if (c == '\n') {
                // Đã nhận đủ 1 dòng
                DeserializationError err = deserializeJson(doc, input);
                if (!err && doc.containsKey("switch")) {
                    bool sw = doc["switch"];
                    digitalWrite(LED_PIN, sw ? HIGH : LOW);
                    Serial.printf("Set LED by serial: %s\n", sw ? "ON" : "OFF");
                }
                input = "";
            } else {
                input += c;
            }
        }
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

void taskDHT20(void *parameter) {
    while (true) {
        dht20.read();
        temperature = dht20.getTemperature();
        humidity = dht20.getHumidity();
        light = analogRead(LIGHT_SENSOR_PIN);  // Read analog value from light sensor
        moisture = analogRead(MOISTURE_PIN);  // Read analog value from light sensor
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
}

void taskThingsBoard(void *parameter) {
    // Không cần kết nối đến ThingsBoard nếu bạn chỉ muốn in ra terminal
    Serial.println("ThingsBoard connection disabled");
    vTaskDelete(NULL); // Xóa task này vì không cần thiết
}

void loop() {

}