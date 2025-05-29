from google.colab import drive
import numpy as np
import pandas as pd
import random
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Flatten
from keras.layers import Conv1D
from keras.layers import MaxPooling1D
from google.colab import auth
auth.authenticate_user()

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io



# Data preprocessing
def split_sequence(sequence, n_steps):
	X, y = list(), list()
	for i in range(len(sequence)):
		# Find the end of this pattern
		end_ix = i + n_steps
		# Check if we are beyond the sequence
		if end_ix > len(sequence)-1:
			break
		# Gather input and output parts of the pattern
		seq_x, seq_y = sequence[i:end_ix], sequence[end_ix]
		X.append(seq_x)
		y.append(seq_y)
	return np.array(X), np.array(y)

# Function to read csv file from google drive
def read_csv_from_drive_link(file_id):
  drive_service = build('drive', 'v3')
  request = drive_service.files().get_media(fileId=file_id)
  downloaded = io.BytesIO()
  downloader = MediaIoBaseDownload(downloaded, request)
  done = False
  while done is False:
    status, done = downloader.next_chunk()

  downloaded.seek(0)
  return pd.read_csv(downloaded)
# Read given train and test sets
# train_data = read_csv_from_drive_link("1CvX-gjGkiPDojF9vG9VQVJ5sBxNCOG1P")
# test_data = read_csv_from_drive_link("1Kvv5EBQFad5PfoEkSgiMKVT1dE-9BglZ")
# train_data = read_csv_from_drive_link("1H1Z7AK3u-keuuF_Y8IabCkN7Uo5ekvR4")
# test_data = read_csv_from_drive_link("1H1Z7AK3u-keuuF_Y8IabCkN7Uo5ekvR4")

train_data = read_csv_from_drive_link("1QcRL4hJ-hJx_KdiOffh33VNDbo8Lol8c")
test_data = read_csv_from_drive_link("1j7n1eDDz76T8zyfvYpOdwGvDhUiY5w0o")
# In ra các cột trong train_data và test_data
print(train_data.columns)  # In danh sách cột trong train_data
print(test_data.columns)   # In danh sách cột trong test_data


# humi_seq_train = train_data['Relative_humidity_room'].tolist()
# humi_seq_test = test_data['Relative_humidity_room'].tolist()
# print(humi_seq_train)  # In danh sách cột trong train_data
# print(humi_seq_test)   # In danh sách cột trong test_data

# Preprocessing steps
# Choose a number of time steps
n_steps = 3
# Split into samples
X, y = split_sequence(humi_seq_train, n_steps)
# Reshape from [samples, timesteps] into [samples, timesteps, features]
n_features = 1
X = X.reshape((X.shape[0], X.shape[1], n_features))

# Define model
model = Sequential()
model.add(Conv1D(filters=64, kernel_size=2, activation='relu', input_shape=(n_steps, n_features)))
model.add(MaxPooling1D(pool_size=2))
model.add(Flatten())
model.add(Dense(50, activation='relu'))
model.add(Dense(1))
model.compile(optimizer='adam', loss='mse')

# Fit model
model.fit(X, y, epochs=200, verbose=1)

# Predict on test set based on the steps
for i in range(10):
  random_num = random.randint(0, len(humi_seq_test)-4)
  x_input = np.array(humi_seq_test[random_num:random_num+n_steps])
  x_input = x_input.reshape((1, n_steps, n_features))
  predicted_value = model.predict(x_input, verbose=0)
  rmse = np.sqrt(np.mean((humi_seq_test[random_num+n_steps] - predicted_value[0][0])**2))
  print("Sequence:", np.array(humi_seq_test[random_num:random_num+n_steps]),"Next value:", humi_seq_test[random_num+n_steps], ", Predicted next value:", predicted_value[0][0], ", RMSE:", rmse)


import paho.mqtt.client as mqttclient
import time
import json
import random
print("Hello Core IOT")
import paho.mqtt.client as mqttclient
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense
import time
import json
import random
import numpy as np

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883
ACCESS_TOKEN_DEVICE_1 = "35jnxpzvq9l256mmq5sg"

# Initialize MQTT client
client = mqttclient.Client("IOT_DEVICE_1")
client.username_pw_set(ACCESS_TOKEN_DEVICE_1)

def subscribed(client, userdata, mid, granted_qos):
    print("Subscribed...")

def recv_message(client, userdata, message):
    print("Received: ", message.payload.decode("utf-8"))
    temp_data = {'value': True}
    try:
        jsonobj = json.loads(message.payload)
        if jsonobj['method'] == "setValue":
            temp_data['value'] = jsonobj['params']
            client.publish('v1/devices/me/attributes', json.dumps(temp_data), 1)
    except:
        pass

def connected(client, usedata, flags, rc):
    if rc == 0:
        print("Connected successfully!!")
        client.subscribe("v1/devices/me/rpc/request/+")
    else:
        print("Connection is failed")

client.on_connect = connected
client.connect(BROKER_ADDRESS, 1883)
client.loop_start()

client.on_subscribe = subscribed
client.on_message = recv_message

# Location coordinates
long = 106.83007174604106
lat = 10.837974010439286

# Model and test data assumptions
# You must define these variables: humi_seq_test and temperature_seq_test

# # Example sequences for testing
# humi_seq_test = [50, 51, 52, 53, 54, 55]  # Example humidity data
# temperature_seq_test = [25, 26, 27, 28, 29, 30]  # Example temperature data
# n_steps = 3  # Number of steps for the input sequence
# n_features = 2  # Number of features (humidity and temperature)

# You should have your trained model here
# Assuming the model is already trained and available as 'model'

# Predict on test set
while True:
    random_num = random.randint(0, len(humi_seq_test) - 4)

    # Create input data by stacking humidity and temperature sequences
    x_input = np.vstack((humi_seq_test[random_num:random_num + n_steps], temperature_seq_test[random_num:random_num + n_steps])).T
    x_input = x_input.reshape((1, n_steps, n_features))  # Reshape to fit model input

    # Predict next values for humidity and temperature
    predicted_value = model.predict(x_input, verbose=0)

    # Calculate RMSE for both humidity and temperature predictions
    rmse_humi = np.sqrt(np.mean((humi_seq_test[random_num + n_steps] - predicted_value[0][0])**2))
    rmse_temp = np.sqrt(np.mean((temperature_seq_test[random_num + n_steps] - predicted_value[0][1])**2))

    # Prepare telemetry data for MQTT
    collect_data = {
        'temperature': float(predicted_value[0][1]),  # Convert numpy float32 to Python float
        'humidity': float(predicted_value[0][0]),     # Convert numpy float32 to Python float
        'rmse_humidity': float(rmse_humi),            # Convert numpy float32 to Python float
        'rmse_temperature': float(rmse_temp),          # Convert numpy float32 to Python float
        'long': long,
        'lat': lat
    }
    print(float(predicted_value[0][1]))
    print(float(predicted_value[0][0]))


    # Publish telemetry data to the dashboard
    client.publish('v1/devices/me/telemetry', json.dumps(collect_data), 1)

    # # Print the results for debugging
    # print(f"Sequence {i}")
    # print("Humidity sequence:", np.array(humi_seq_test[random_num:random_num + n_steps]),
    #       ", Predicted humidity:", predicted_value[0][0],
    #       ", RMSE:", rmse_humi)

    # print("Temperature sequence:", np.array(temperature_seq_test[random_num:random_num + n_steps]),
    #       ", Predicted temperature:", predicted_value[0][1],
    #       ", RMSE:", rmse_temp)

    # print("-" * 20)

    # # Wait a short period before sending the next data (for example, 5 seconds)
    time.sleep(5)


