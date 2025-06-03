import numpy as np
import pandas as pd
import serial
from keras.models import Sequential
from keras.layers import Dense, Flatten, Conv1D, MaxPooling1D, Input, Dropout
import paho.mqtt.client as mqttclient
import time
import json
from sklearn.preprocessing import MinMaxScaler
from keras.callbacks import EarlyStopping
from keras.optimizers import Adam

TOKEN = "ttrv0asoe3tln5zqjswc"  # Device token from CoreIoT/ThingsBoard
BROKER = "app.coreiot.io"       # MQTT Broker
PORT = 1883

# --- Keras Model Preparation ---
def split_sequences(sequences, n_steps):
    X, y = list(), list()
    for i in range(len(sequences)):
        end_ix = i + n_steps
        if end_ix > len(sequences)-1:
            break
        seq_x, seq_y = sequences[i:end_ix, :], sequences[end_ix, :]
        X.append(seq_x)
        y.append(seq_y)
    return np.array(X), np.array(y)

train_data = pd.read_csv(r"train.csv")
test_data = pd.read_csv(r"test.csv")

# Check for missing values
print("Missing values in training data:", train_data.isnull().sum())

# Handle missing values if any
train_data = train_data.fillna(method='ffill')  # Forward fill missing values

# Extract and normalize the data
scaler = MinMaxScaler()

humi_seq_train = np.array(train_data['humidity'])
temp_seq_train = np.array(train_data['temperature'])
light_seq_train = np.array(train_data['lighting'])
moisture_seq_train = np.array(train_data['moisture'])

# Reshape and normalize the data
humi_seq_train = scaler.fit_transform(humi_seq_train.reshape(-1, 1))
temp_seq_train = scaler.fit_transform(temp_seq_train.reshape(-1, 1))
light_seq_train = scaler.fit_transform(light_seq_train.reshape(-1, 1))
moisture_seq_train = scaler.fit_transform(moisture_seq_train.reshape(-1, 1))

# Print some statistics
print("Data shapes after preprocessing:")
print("Humidity:", humi_seq_train.shape)
print("Temperature:", temp_seq_train.shape)
print("Light:", light_seq_train.shape)
print("Moisture:", moisture_seq_train.shape)

# Check for any remaining NaN values
print("NaN values after preprocessing:", np.isnan(humi_seq_train).sum() + np.isnan(temp_seq_train).sum() + np.isnan(light_seq_train).sum() + np.isnan(moisture_seq_train).sum())

# Combine features
dataset = np.hstack((humi_seq_train, temp_seq_train, light_seq_train, moisture_seq_train))  # Combine all features
n_steps = 3
X, y = split_sequences(dataset, n_steps)
n_features = X.shape[2]

# Create model with better initialization and parameters
model = Sequential([
    Input(shape=(n_steps, n_features)),
    Conv1D(filters=32, kernel_size=2, activation='relu', kernel_initializer='he_normal', padding='same'),
    MaxPooling1D(pool_size=1),  # Reduced pool size to preserve sequence length
    Conv1D(filters=64, kernel_size=2, activation='relu', kernel_initializer='he_normal', padding='same'),
    Flatten(),
    Dense(100, activation='relu', kernel_initializer='he_normal'),
    Dropout(0.2),  # Add dropout to prevent overfitting
    Dense(50, activation='relu', kernel_initializer='he_normal'),
    Dense(n_features, activation='linear')  # Linear activation for regression
])

# Compile with a smaller learning rate
model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])

# Add early stopping to prevent overfitting
early_stopping = EarlyStopping(
    monitor='val_loss',
    patience=20,
    restore_best_weights=True,
    min_delta=0.0001
)

# Print model summary
model.summary()

# Fit with validation split and early stopping
history = model.fit(
    X, y,
    epochs=200,
    batch_size=32,
    verbose=1,
    validation_split=0.2,
    callbacks=[early_stopping]
)

def prediction(array):
    x_input = np.array(array).reshape((1, n_steps, n_features))
    predicted_value = model.predict(x_input, verbose=0)
    # print("Predicted humidity:", predicted_value[0][0])
    # print("Predicted temp:", predicted_value[0][1])
    # print("Predicted light:", predicted_value[0][2])
    # print("Predicted moisture:", predicted_value[0][3])
    # print("-" * 20)
    temp_1 = float(predicted_value[0][1])
    humi_1 = float(predicted_value[0][0])
    light_1 = float(predicted_value[0][2])
    moisture_1 = float(predicted_value[0][3])
    return temp_1, humi_1, light_1, moisture_1

# --- MQTT Setup ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Kết nối MQTT thành công!")
        # Subscribe to RPC requests
        client.subscribe("v1/devices/me/rpc/request/+")
        print("Đã đăng ký nhận RPC requests từ CoreIOT")
    else:
        print(f"Kết nối MQTT thất bại với mã lỗi: {rc}")
        # rc=0: Kết nối thành công
        # rc=1: Sai protocol
        # rc=2: Client ID không hợp lệ
        # rc=3: Server không khả dụng
        # rc=4: Sai username/password
        # rc=5: Không được phép kết nối

def on_publish(client, userdata, mid):
    print(f"Đã gửi dữ liệu lên CoreIOT với message ID: {mid}")

def on_disconnect(client, userdata, rc):
    global reconnect_count
    if rc != 0:
        print(f"Mất kết nối MQTT với mã lỗi: {rc}, đang thử kết nối lại...")
        time.sleep(5)  # Đợi 5 giây trước khi kết nối lại
        try:
            client.reconnect()
        except Exception as e:
            print(f"Lỗi khi kết nối lại: {e}")
    else:
        print("Đã ngắt kết nối MQTT")

def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        print("RPC received:", payload)
        if payload.get("method") == "setSwitch":
            switch_state = payload.get("params")
            ser.write((json.dumps({"switch": switch_state}) + "\n").encode())
        if payload.get("method") == "setPump":
            switch_state = payload.get("params")
            ser.write((json.dumps({"pump": switch_state}) + "\n").encode())
        if payload.get("method") == "setFan":
            switch_state = payload.get("params")
            ser.write((json.dumps({"fan": switch_state}) + "\n").encode())
    except Exception as e:
        print("RPC error:", e)

client = mqttclient.Client()
client.username_pw_set(TOKEN)
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish
client.on_disconnect = on_disconnect

try:
    print(f"Đang kết nối đến MQTT broker {BROKER}:{PORT}")
    client.connect(BROKER, PORT)
    client.loop_start()
except Exception as e:
    print(f"Lỗi khi kết nối MQTT: {e}")

# --- Serial Setup ---
ser = serial.Serial('COM5', 115200, timeout=2)
print(f"Đã mở cổng Serial COM5: {ser.is_open}")

# --- Main Loop ---
array = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]  # [humidity][temp][light][moisture]
attemp = 0
temp = None
humi = None
light = None
moisture = None

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        print(f"Dữ liệu nhận được từ Serial: {line}")
        if not line:
            print("Không có dữ liệu từ Serial, đang đợi...")
            continue

        if "Temperature:" in line and "Humidity:" in line:
            # Parse temperature and humidity
            temp_str = line.split("Temperature:")[1].split("°C")[0].strip()
            humi_str = line.split("Humidity:")[1].split("%")[0].strip()
            temp = float(temp_str)
            humi = float(humi_str)
            print(f"Đã đọc được - Nhiệt độ: {temp}°C, Độ ẩm: {humi}%")
        
        if "Light:" in line:
            # Parse light
            light_str = line.split("Light:")[1].split("lux")[0].strip()
            light = float(light_str)/10
            print(f"Đã đọc được - Ánh sáng: {light} lux")
            
        if "Moisture:" in line:
            # Parse moisture
            moisture_str = line.split("Moisture:")[1].split("%")[0].strip()
            moisture = float(moisture_str)
            print(f"Đã đọc được - Độ ẩm đất: {moisture}%")   
            
        if "[Received command]:" in line:
            command = line.split("[Received command]:")[1].strip()
            print(f"Đã nhận lệnh từ CoreIOT: {command}")
           # Gửi dữ liệu lên MQTT, thay giá trị None bằng 0
        
        if "[Serial] Test command received successfully!" in line:
            print("Đã update led state thành công!")
        try:
            # First send the raw sensor data
            sensor_data = {
                'temperature': temp if temp is not None else 0,
                'humidity': humi if humi is not None else 0,
                'light': light if light is not None else 0,
                'moisture': moisture if moisture is not None else 0
            }
            print(f"Gửi dữ liệu sensor lên CoreIOT: {sensor_data}")
            result = client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), qos=1, retain=False)
            if not result.is_published():
                result.wait_for_publish()
            print("Đã gửi dữ liệu sensor thành công!")

            # Xử lý phần prediction
            if attemp < 3:
                # Store current values in array
                array[0][attemp] = float(humi if humi is not None else 0)
                array[1][attemp] = float(temp if temp is not None else 0)
                array[2][attemp] = float(light if light is not None else 0)
                array[3][attemp] = float(moisture if moisture is not None else 0)
                attemp += 1
                # print(f"Đã lưu vào array lần {attemp}: Humidity={humi if humi is not None else 0}, Temp={temp if temp is not None else 0}, Light={light if light is not None else 0}, Moisture={moisture if moisture is not None else 0}")
                # print("Current array state:", array)
            
            elif attemp == 3:
                attemp += 1
                # Convert array to float and normalize
                norm_array = [
                    [scaler.transform([[float(x)]])[0][0] for x in array[0]],
                    [scaler.transform([[float(x)]])[0][0] for x in array[1]],
                    [scaler.transform([[float(x)]])[0][0] for x in array[2]],
                    [scaler.transform([[float(x)]])[0][0] for x in array[3]]
                ]
                print("Normalized array:", norm_array)
                
                # Make prediction
                temp_predict, humi_predict, light_predict, moisture_predict = prediction(norm_array)
                
                # Transform predictions back to original scale
                temp_predict = float(scaler.inverse_transform([[temp_predict]])[0][0])/10
                humi_predict = float(scaler.inverse_transform([[humi_predict]])[0][0])/4
                light_predict = float(scaler.inverse_transform([[light_predict]])[0][0])
                moisture_predict = float(scaler.inverse_transform([[moisture_predict]])[0][0])
                
                # Send predictions to CoreIOT
                collect_data = {
                    'temperature': temp if temp is not None else 0,
                    'humidity': humi if humi is not None else 0,
                    'light': light if light is not None else 0,
                    'moisture': moisture if moisture is not None else 0,
                    'temperature_predict': temp_predict,
                    'humidity_predict': humi_predict,
                    'light_predict': light_predict,
                    'moisture_predict': moisture_predict
                }
                print(f"Đang gửi dữ liệu dự đoán lên CoreIOT: {collect_data}")
                result = client.publish('v1/devices/me/telemetry', json.dumps(collect_data), qos=1, retain=False)
                if not result.is_published():
                    result.wait_for_publish()
                print("Đã gửi dữ liệu dự đoán thành công!")
            else:
                # Update array with previous values and last prediction
                array = [
                    [float(array[0][1]), float(array[0][2]), float(humi_predict)],
                    [float(array[1][1]), float(array[1][2]), float(temp_predict)],
                    [float(array[2][1]), float(array[2][2]), float(light_predict)],
                    [float(array[3][1]), float(array[3][2]), float(moisture_predict)]
                ]
                
                # Make new prediction with updated array
                norm_array = [
                    [scaler.transform([[x]])[0][0] for x in array[0]],
                    [scaler.transform([[x]])[0][0] for x in array[1]],
                    [scaler.transform([[x]])[0][0] for x in array[2]],
                    [scaler.transform([[x]])[0][0] for x in array[3]]
                ]
                
                temp_predict, humi_predict, light_predict, moisture_predict = prediction(norm_array)
                
                # Transform predictions back to original scale
                temp_predict = float(scaler.inverse_transform([[temp_predict]])[0][0])/10
                humi_predict = float(scaler.inverse_transform([[humi_predict]])[0][0])/4
                light_predict = float(scaler.inverse_transform([[light_predict]])[0][0])
                moisture_predict = float(scaler.inverse_transform([[moisture_predict]])[0][0])
                
                # Send new predictions to CoreIOT
                collect_data = {
                    'temperature': temp,
                    'humidity': humi,
                    'light': light,
                    'moisture': moisture,
                    'temperature_predict': temp_predict,
                    'humidity_predict': humi_predict,
                    'light_predict': light_predict,
                    'moisture_predict': moisture_predict
                }
                print(f"Đang gửi dữ liệu dự đoán lên CoreIOT: {collect_data}")
                result = client.publish('v1/devices/me/telemetry', json.dumps(collect_data), qos=1, retain=False)
                if not result.is_published():
                    result.wait_for_publish()
                print("Đã gửi dữ liệu dự đoán thành công!")
                
            # print("Current array state:", array)
        except Exception as e:
            print(f"Lỗi khi xử lý và gửi dữ liệu: {e}")

            # Reset các giá trị để đọc lần tiếp theo
            temp = None
            humi = None
            light = None
            moisture = None

    except Exception as e:
        print(f"Lỗi đọc Serial: {e}")
        continue

    if not client.is_connected():
        print("Mất kết nối MQTT, đang thử kết nối lại...")
        try:
            client.reconnect()
        except Exception as e:
            print(f"Lỗi khi kết nối lại: {e}")