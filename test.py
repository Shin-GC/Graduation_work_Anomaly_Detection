import os
import numpy as np
import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers
from matplotlib import pyplot as plt
import datetime
import DB
import DB_csv
path = os.getcwd()
now = datetime.datetime.now() + datetime.timedelta( hours=-1)
TIME_STEPS = 24
user_size = DB.user_size()
score_time=now.strftime("%H")


# TIME_STEPS훈련 데이터에서 연속 된 데이터 값을 결합하는 시퀀스를 만듭니다 .
def create_sequences(values, time_steps=TIME_STEPS):
    output = []
    for i in range(len(values) - time_steps):
        output.append(values[i : (i + time_steps)])
    return np.stack(output)

Traning_data = pd.read_csv(
f'{path}\Treaning\Time_Serial_Anomaly_Data.csv', parse_dates=True, index_col="timestamp"
, usecols=['timestamp', 'temp', 'humidity'])

    #LOAD_DATA head print
print(Traning_data.head(1))

    #학습 데이터 정규화
training_mean = Traning_data.mean() #평균값
training_std = Traning_data.std() #표준편차
Traning_data_value = (Traning_data - training_mean) / training_std #Data - 평균 / 편차
print(Traning_data_value.head())
print("Number of training samples:", len(Traning_data_value))

x_train = create_sequences(Traning_data_value.values)
print("Training input shape: ", x_train.shape) #행, 열
print("x_train.shape: ", x_train.shape[0])

model = keras.Sequential( #순차 모델
    [
        #Input 텐서를 인스턴스화 한다 (sharp(24,1)) == 이는 배치크기가 24인  Layer 가 하나 생성된다.
        layers.Input(shape=(x_train.shape[1], x_train.shape[2])),
        layers.Conv1D(
            filters=32, kernel_size=7, padding="same", strides=2, activation="relu"
        ),
        layers.Dropout(rate=0.2),
        layers.Conv1D(
            filters=16, kernel_size=7, padding="same", strides=2, activation="relu"
        ),
        layers.Conv1DTranspose(
            filters=16, kernel_size=7, padding="same", strides=2, activation="relu"
        ),
        layers.Dropout(rate=0.2),
        layers.Conv1DTranspose(
            filters=32, kernel_size=7, padding="same", strides=2, activation="relu"
        ),
        layers.Conv1DTranspose(filters=1, kernel_size=7, padding="same"),
    ]
    )
model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001), loss="mse")
model.summary()


history = model.fit(
    x_train,
    x_train,
    epochs=5,
    batch_size=100,
    validation_split=0.1,
    callbacks=[
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, mode="min")
    ],
)

x_train_pred = model.predict(x_train)
train_mae_loss = np.mean(np.abs(x_train_pred - x_train), axis=1)

# 성능 임계 값을 가져옵니다.
threshold = np.max(train_mae_loss)
print("Reconstruction error threshold: ", threshold)
temp_result = []
temp_anomaly_score = []


    # 테스트 데이터
print(f'{path}\Data\\test.csv')
Test_data = pd.read_csv(
    f'{path}\\Data\\test.csv', parse_dates=True, index_col="timestamp"
    ,usecols=['timestamp','temp','humidity'])

df_test_value = (Test_data - training_mean) / training_std
    # 테스트 값에서 시퀀스를 만듭니다.
x_test = create_sequences(df_test_value.values)
print("Test input shape: ", x_test.shape)

    # 테스트 성능을 가져옵니다.
x_test_pred = model.predict(x_test)
test_mae_loss = np.mean(np.abs(x_test_pred - x_test), axis=1)
test_mae_loss = test_mae_loss.reshape((-1))


# 이상이있는 모든 샘플을 감지합니다.
anomalies = test_mae_loss > threshold
print("Anomaly data(count) : ", np.sum(anomalies))
print("Indices of anomaly samples: ", np.where(anomalies))

print(f"Anomaly : {anomalies}")

DB.anomaly_score_temp(0,test_mae_loss, score_time)
DB.threshold_temp(0,threshold)

if np.sum(anomalies) == 0 :
    temp_result.append(0)

elif np.sum(anomalies) !=0 :
    temp_result.append(1)

    #Anomaly Data RED
    # 데이터 i는 샘플 [(i-timesteps + 1) ~ (i)]이 이상이면 이상입니다.
anomalous_data_indices = []
for data_idx in range(len(df_test_value)):
    if np.all(anomalies[data_idx - TIME_STEPS + 1 : data_idx]):
        anomalous_data_indices.append(data_idx)

print(f"anomalous_data_indices : {anomalous_data_indices}")


df_subset = Test_data.iloc[anomalous_data_indices]
print(f"df_subset : {df_subset}")
fig, ax = plt.subplots()
Test_data.plot(legend=False, ax=ax)
df_subset.plot(legend=False, ax=ax, color="r")
plt.title('Temp_Detection')
#plt.savefig(f'C:/Users/GM/eclipse-workspace/AI_Project_Hoseo_2021/WebContent/img/Temp_Detection{time}_{i}.png')
plt.show()