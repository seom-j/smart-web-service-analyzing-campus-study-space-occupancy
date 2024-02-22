# -*- coding: utf-8 -*-
"""
DB 연동 / LSTM 모델_최종.ipynb
!pip install pymysql
"""


"""## 데이터 불러오기 & 활용"""

import pymysql
from prettytable import PrettyTable
import pandas as pd
import matplotlib.pyplot as plt


df = None

conn = pymysql.connect(
    # 접속 정보 입력
)

# table_name = 테이블 이름 입력

try:
    # 테이블 데이터를 조회하는 쿼리 실행
    select_data_query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(select_data_query, conn)

    # 데이터프레임 출력
    print(df)

finally:
    # 연결 닫기
    conn.close()

print(df)

# 1. seat 열 삭제
# 2. index 제거
df.reset_index(drop=True, inplace=True)

# 3. id - 195까지만 추출
df = df[df['id'] <= 195]

# 4. 컬럼 순서 saturation이 맨 뒤에 오도록
df = df[['id', 'past_date', 'past_time', 'saturation']]

# 수정된 데이터프레임 출력
print(df)

df.head(40)

"""### df 23일까지 잘 생성 되었나 확인"""

# 날짜 목록 가져오기
date_list = df['past_date'].unique()

# 날짜별로 서로 다른 서브플롯 생성
fig, axes = plt.subplots(len(date_list), 1, figsize=(12, 6*len(date_list)), sharex=True)

for i, date in enumerate(date_list):
    # 각 날짜에 해당하는 데이터 추출
    date_df = df[df['past_date'] == date]

    # 그래프 그리기
    axes[i].plot(date_df['past_time'], date_df['saturation'], marker='o', linestyle='-', color='blue')

    # y 축 레이블 및 제목 추가
    axes[i].set_ylabel('Saturation')
    axes[i].set_title(f'Saturation on {date}')

    # 그리드 추가
    axes[i].grid(True)

# x 축 레이블 추가
axes[-1].set_xlabel('Time')

# 그래프 표시
plt.tight_layout()
plt.show()

date_list

date_df.head(40)

# 날짜별 데이터 개수 출력
date_counts = df['past_date'].value_counts().sort_index()
print("날짜별 데이터 개수:")
print(date_counts)

"""
데이터 전처리  
시간과 날짜를 결합하여 시계열 데이터를 생성하고, 이를 훈련 데이터로 변환
"""

from sklearn.preprocessing import MinMaxScaler
import numpy as np

# 날짜와 시간을 결합하여 새로운 'datetime' 열을 생성
df['datetime'] = pd.to_datetime(df['past_date'] + ' ' + df['past_time'].astype(str) + ':00')

# 'datetime' 열을 인덱스로 설정
df.set_index('datetime', inplace=True)

# 'saturation' 열만 선택
data = df[['saturation']]

# 데이터 정규화
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data)

# 시계열 데이터를 생성하기 위한 함수 정의
def create_dataset(dataset, look_back=1):
    X, Y = [], []
    for i in range(len(dataset)-look_back):
        a = dataset[i:(i+look_back), 0]
        X.append(a)
        Y.append(dataset[i + look_back, 0])
    return np.array(X), np.array(Y)

# 24시간을 기준으로 데이터셋 생성
look_back = 24
X, Y = create_dataset(scaled_data, look_back)

# 데이터셋 분할 (훈련 데이터와 테스트 데이터)
train_size = int(len(X) * 0.80)
test_size = len(X) - train_size
trainX, testX = X[0:train_size], X[train_size:len(X)]
trainY, testY = Y[0:train_size], Y[train_size:len(Y)]

# LSTM에 필요한 형태로 데이터 형태 변경 ([samples, time steps, features])
trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))

trainX.shape, testX.shape, trainY.shape, testY.shape

""" 모델을 구축 / 훈련"""

from keras.models import Sequential
from keras.layers import LSTM, Dense

# LSTM 모델 생성
model = Sequential()
model.add(LSTM(50, input_shape=(trainX.shape[1], trainX.shape[2])))
model.add(Dense(1))

# 모델 컴파일
model.compile(loss='mean_squared_error', optimizer='adam')

# 모델 훈련
model.fit(trainX, trainY, epochs=100, batch_size=1, verbose=2)

""" 마지막 24시간 데이터"""

# 마지막 24시간 데이터 선택
last_24_hours = scaled_data[-24:]
last_24_hours = np.reshape(last_24_hours, (1, 1, 24))

# 예측 수행
predicted_saturation = model.predict(last_24_hours)
predicted_saturation = scaler.inverse_transform(predicted_saturation)

# 예측 결과 출력
print(predicted_saturation)

predicted_saturation = []
for i in range(14):  # 10월 24일의 09시부터 22시까지 14개의 시간대에 대해 반복
    # 마지막 24시간 데이터 선택
    last_24_hours = scaled_data[-24 - i:-i if i != 0 else None]
    last_24_hours = np.reshape(last_24_hours, (1, 1, 24))

    # 예측 수행
    predicted_value = model.predict(last_24_hours)
    predicted_saturation.append(predicted_value[0, 0])

# 예측 결과를 원래의 스케일로 되돌림
predicted_saturation = scaler.inverse_transform([predicted_saturation])

# 예측 결과를 데이터 프레임으로 변환
predicted_saturation = predicted_saturation.reshape(-1, 1)  # 배열 형태 변경
predicted_df = pd.DataFrame(predicted_saturation, index=predicted_dates, columns=['Predicted Saturation'])

""" 알맞게 되었는지 시각화"""

import matplotlib.pyplot as plt
import pandas as pd

# 예측 결과를 데이터 프레임으로 변환
predicted_dates = pd.date_range(start='2023-10-24 09:00', end='2023-10-24 22:00', freq='H')
predicted_df = pd.DataFrame(predicted_saturation, index=predicted_dates, columns=['Predicted Saturation'])

# 시각화
plt.figure(figsize=(10, 6))
plt.plot(predicted_df.index, predicted_df['Predicted Saturation'], color='blue', marker='o', linestyle='dashed', label='Predicted Saturation')
plt.title('Predicted Saturation on 2023-10-24')
plt.xlabel('Time')
plt.ylabel('Saturation')
plt.xticks(rotation=45)
plt.legend()
plt.show()