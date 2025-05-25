#include <Wire.h>
#include <DHT20.h>
#include <Adafruit_BMP280.h>

// Cảm biến
DHT20 dht20(&Wire);  // Truyền tham chiếu đối tượng Wire vào
Adafruit_BMP280 bmp;

// Cấu hình chân I2C tùy chỉnh
#define SDA_PIN 11
#define SCL_PIN 12

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
}

void loop() {
  Serial.println("----- Đọc dữ liệu -----");

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
