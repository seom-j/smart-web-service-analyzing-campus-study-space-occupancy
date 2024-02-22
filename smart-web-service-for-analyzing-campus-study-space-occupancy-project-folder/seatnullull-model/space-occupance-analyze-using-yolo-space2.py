#!/usr/bin/env python

from multiprocessing import Manager, Process
import datetime
import pymysql
import random
import asyncio
import websockets
import time
import cv2
import json
import websockets
import torch
import numpy as np
import subprocess
import json

def database(people,obj):
    conn= pymysql.connect(
        # 접속 정보 입력
    )

    cur = conn.cursor()
    sql2 = "insert into distributionAverage (distribution, hour, minute,date) values(%s, %s, %s,%s)"

    totalPeople=28 #전체 자리 수

    # 함수
    def addData(distribution):
        vals = (distribution,nowHour,nowMinute,nowDate)
        cur.execute(sql2,vals)
        conn.commit()

    def calcDistribution():
        nowPeople = 0
        for i in people:
            nowPeople += i
        avg = int(nowPeople / totalPeople * 100)
        return  avg
    
    tz = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(tz=tz)

    nowHour = now.hour
    nowDate = now.strftime("%Y-%m-%d")
    date = ""
    hour = 0

    print("Start")

    nowMinute = datetime.datetime.now(tz=tz).minute
    distribution = calcDistribution()
    print("시작하기전",nowHour,nowMinute)

    while(1):
        tmp = datetime.datetime.now(tz=tz)
        if(tmp.hour == 22):
            break

        if(tmp.minute != nowMinute):
            print(tmp.hour,"분이지남","  ",nowMinute,"분")
            distribution = calcDistribution()# 이자리에 값들어갈거임
            addData(distribution)
            nowMinute = tmp.minute


def websocket(people, obj):
  print("p / o " ,people, obj)

  async def hello():
    retry_interval=3
    uri = "ws://seatnullnull.com:8080/ws/data"

    async def connect_websocket():
      while True:
        try:
          async with websockets.connect(uri, ping_interval=None) as websocket:
            print("Connected successfully!")
            await websocket_handler(websocket)
        except Exception as ex:
          print(f"Connection attempt failed: {ex}")
          await asyncio.sleep(retry_interval)
    async def websocket_handler(websocket):
        while True:
            send = []
            for i in range(len(people)):
                data = {"id": i+7, "pp": people[i], "st": obj[i],"where":1}
                send.append(data)
            try:
                await websocket.send(json.dumps(send))
             
            except websockets.ConnectionClosed as e:
                print(e)
                break  
            await asyncio.sleep(5)
    await connect_websocket()

  asyncio.get_event_loop().run_until_complete(hello())
  asyncio.get_event_loop().run_forever()

def model(people,obj):
    # YOLOv5 모델 불러오기
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

    # 관심 영역 정의 (네모모양 영역)
    rectangles = [(0, 700, 1170, 1676), (520, 564,1133, 839), (691, 447, 1208, 663), (825, 387, 1193, 509), (1550, 414, 2000, 818)]
    while True:
        subprocess.run(["libcamera-still", "-t", "10000", "-o", "test.jpg"], check=True, capture_output=True)
        frame = cv2.flip(cv2.imread("test.jpg"), 0)
        print("저장 완료")
        time.sleep(2)

        # 관심 영역에 빨간색 사각형 그리기
        for rect in rectangles:
            x1, y1, x2, y2 = rect
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        for i, rect in enumerate(rectangles):
            x1, y1, x2, y2 = rect
            roi = frame[y1:y2, x1:x2]  # 관심 영역 추출
            results = model(roi)  # YOLOv5 모델로 객체 검출 수행

            # 관심 영역에서 사람 수 계산
            num_persons = len(results.pred[0][results.pred[0][:, 5] == 0])
            print(num_persons)
            people[i] = num_persons

            # 관심 영역에 노트북, 컵, 책, 가방, 핸드백이 있는지 여부 판단
            object_present = any([
                results.pred[0][results.pred[0][:, 5] == 63].any(),  # 노트북
                results.pred[0][results.pred[0][:, 5] == 41].any(),  # 컵
                results.pred[0][results.pred[0][:, 5] == 73].any(),  # 책
                results.pred[0][results.pred[0][:, 5] == 24].any(),  # 가방
                results.pred[0][results.pred[0][:, 5] == 26].any()   # 핸드백
            ])
            # obj.append(object_present)
            obj[i] = object_present


            # 검출된 객체에 초록색 바운딩 박스 그리기
            for result in results.pred[0]:
                label = int(result[5])
                if label in [0, 63, 41, 73, 24, 26]:
                    x1, y1, x2, y2 = result[:4].int().cpu().numpy()
                    cv2.rectangle(roi, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 화면에 관심 영역별로 사람 수와 객체 존재 여부 표시
        for i, rect in enumerate(rectangles):
            x1, y1, _, _ = rect
            cv2.putText(frame, f"Area {i + 1}'s people: {people[i]}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, f"Area {i + 1}'s objects: {'Yes' if obj[i] else 'No'}", (x1, y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.imwrite('output.jpg', frame)
        time.sleep(2)

        # 결과를 화면에 표시
#        cv2.imshow('YOLOv5 Space Congestion Analysis', frame)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 웹캠 해제 및 창 닫기
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    manager = Manager()

    #테이블 개수 제한 range로, 6개로 제한
    people = manager.list(range(6))
    obj = manager.list(range(6))

    for i in range(6):
        people[i] = 0
        obj[i] = 0

    p0 = Process(target=database,args=(people,obj))
    p1 = Process(target=websocket,args=(people,obj))
    p2 = Process(target=model, args=(people,obj))

    p0.start()
    p1.start()
    p2.start()

    p0.join()
    p1.join()
    p2.join()
