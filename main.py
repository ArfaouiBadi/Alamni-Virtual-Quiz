import os
import cv2
import csv
from cvzone.HandTrackingModule import HandDetector
import cvzone
import time
import json
import sys
import requests
import random
username = sys.argv[1] if len(sys.argv) > 1 else 'User'

cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)
detector = HandDetector(detectionCon=0.8)

class MCQ():
    def __init__(self, data):
        self.question = data[0]
        self.choice1 = data[1]
        self.choice2 = data[2]
        self.choice3 = data[3]
        self.choice4 = data[4]
        self.answer = int(data[5])
        self.userAns = None

    def update(self, cursor, bboxs, img):
        for x, bbox in enumerate(bboxs):
            x1, y1, x2, y2 = bbox
            if x1 < cursor[0] < x2 and y1 < cursor[1] < y2:
                self.userAns = x + 1
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), cv2.FILLED)

def save_score(name, score):
    leaderboard = []
    if os.path.exists('leaderboard.json') and os.path.getsize('leaderboard.json') > 0:
        with open('leaderboard.json', 'r') as f:
            try:
                leaderboard = json.load(f)
            except json.JSONDecodeError:
                print("Error decoding JSON from leaderboard.json")

    leaderboard.append({'name': name, 'score': score})
    leaderboard = sorted(leaderboard, key=lambda x: x['score'], reverse=True)

    with open('leaderboard.json', 'w') as f:
        json.dump(leaderboard, f)
def send_score_to_server(name, score):
    # Send score to Spring Boot server
    spring_boot_url = 'http://localhost:8000/api/submit-score'
    data = {'username': name, 'score': score}
    try:
        response = requests.post(spring_boot_url, json=data)
        if response.status_code == 200:
            print("Score submitted successfully to Spring Boot server")
        else:
            print("Failed to submit score to Spring Boot server")
    except requests.exceptions.RequestException as e:
        print(f"Error submitting score to Spring Boot server: {e}")

    # Send score to Angular frontend
    angular_url = 'http://localhost:4200/api/submit-score'
    try:
        response = requests.post(angular_url, json=data)
        if response.status_code == 200:
            print("Score submitted successfully to Angular frontend")
        else:
            print("Failed to submit score to Angular frontend")
    except requests.exceptions.RequestException as e:
        print(f"Error submitting score to Angular frontend: {e}")
def get_leaderboard():
    try:
        with open('leaderboard.json', 'r') as f:
            leaderboard = json.load(f)
    except FileNotFoundError:
        leaderboard = []
    return leaderboard

def start_quiz(username):
    pathCSV = "generated_questions.csv"
    with open(pathCSV, newline='\n', encoding='utf-8') as f:
        reader = csv.reader(f)
        dataAll = list(reader)[1:]

    random.shuffle(dataAll)
    dataAll = dataAll[:10]

    mcqList = []
    for q in dataAll:
        mcqList.append(MCQ(q))

    print("Total MCQ Objects Created:", len(mcqList))

    qNo = 0
    qTotal = len(dataAll)

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to capture image")
            continue

        img = cv2.flip(img, 1)
        hands, img = detector.findHands(img, flipType=False)
        if qNo < qTotal:
            mcq = mcqList[qNo]

            img, bbox = cvzone.putTextRect(img, mcq.question, [100, 100], 1, 4, offset=10, border=1, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            img, bbox1 = cvzone.putTextRect(img, mcq.choice1, [100, 250], 1, 3, offset=10, border=1, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            img, bbox2 = cvzone.putTextRect(img, mcq.choice2, [600, 250], 1, 3, offset=10, border=1, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            img, bbox3 = cvzone.putTextRect(img, mcq.choice3, [100, 400], 1, 3, offset=10, border=1, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            img, bbox4 = cvzone.putTextRect(img, mcq.choice4, [600, 400], 1, 3, offset=10, border=1, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)

            if hands:
                lmList = hands[0]['lmList']
                if len(lmList) > 12:
                    try:
                        cursor = lmList[8][:2]
                        result = detector.findDistance(lmList[8][:2], lmList[12][:2])
                        length = result[0]
                        if length < 35:
                            mcq.update(cursor, [bbox1, bbox2, bbox3, bbox4], img)
                            if mcq.userAns is not None:
                                time.sleep(0.5)
                                qNo += 1

                    except ValueError as ve:
                        print("ValueError:", ve)
                    except IndexError as ie:
                        print("IndexError:", ie)
                    except Exception as e:
                        print("Unexpected Error:", e)
        else:
            score = 0
            for mcq in mcqList:
                if mcq.answer == mcq.userAns:
                    score += 1
            score = round((score / qTotal) * 100, 2)
            save_score(username, score)
            send_score_to_server(username, score)
            img, _ = cvzone.putTextRect(img, "Quiz Completed", [250, 300], 2, 2, offset=50, border=5, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            img, _ = cvzone.putTextRect(img, f'Your Score: {score}%', [700, 300], 2, 2, offset=50, border=5, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)
            cv2.imshow("Img", img)
            cv2.waitKey(1)
            return score


        barValue = 150 + (950 // qTotal) * qNo
        cv2.rectangle(img, (150, 600), (barValue, 650), (0, 255, 0), cv2.FILLED)
        cv2.rectangle(img, (150, 600), (1100, 650), (255, 0, 255), 5)
        img, _ = cvzone.putTextRect(img, f'{round((qNo / qTotal) * 100)}%', [1130, 635], 2, 2, offset=16, colorR=(200, 200, 200), colorT=(0, 0, 0), font=cv2.FONT_HERSHEY_SIMPLEX)

        cv2.imshow("Img", img)
        cv2.waitKey(1)