import os
import pickle
import mediapipe as mp
import cv2
import numpy as np
from sklearn.preprocessing import LabelEncoder

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.3)

DATA_DIR = 'SignToTextConversion/SignToText/Data' # Directory containing gesture videos
SEQUENCE_LENGTH = 30  # Frames per gesture
FEATURE_SIZE = 126     # 21 landmarks × 2 hands × 2 (x, y)

data = []
labels = []
label_names = sorted(os.listdir(DATA_DIR))
label_encoder = LabelEncoder()

for dir_ in label_names:
    label = dir_
    for video_path in os.listdir(os.path.join(DATA_DIR, dir_)):
        cap = cv2.VideoCapture(os.path.join(DATA_DIR, dir_, video_path))
        sequence = []

        while len(sequence) < SEQUENCE_LENGTH and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (640, 340))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(frame_rgb)
            landmarks = []

            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
                for hand_landmarks in results.multi_hand_landmarks:
                    for point in hand_landmarks.landmark:
                        landmarks.extend([point.x, point.y, point.z])
                if hand_count == 1:
                    landmarks.extend([0] * (FEATURE_SIZE - len(landmarks)))

            if len(landmarks) < FEATURE_SIZE:
                landmarks.extend([0] * (FEATURE_SIZE - len(landmarks)))
            elif len(landmarks) > FEATURE_SIZE:
                landmarks = landmarks[:FEATURE_SIZE]

            sequence.append(landmarks)

        cap.release()

        # Pad or trim sequence to fixed length
        if len(sequence) < SEQUENCE_LENGTH:
            sequence.extend([[0] * FEATURE_SIZE] * (SEQUENCE_LENGTH - len(sequence)))
        sequence = sequence[:SEQUENCE_LENGTH]

        data.append(sequence)
        labels.append(label)

labels = label_encoder.fit_transform(labels)
data = np.array(data)  # Shape: (num_samples, SEQUENCE_LENGTH, FEATURE_SIZE)
labels = np.array(labels)

with open('data_seq1.pickle', 'wb') as f:
    pickle.dump({'data': data, 'labels': labels, 'label_map': label_encoder.classes_}, f)

print("Sequential dataset saved successfully!")
