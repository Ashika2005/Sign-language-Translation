import cv2
import mediapipe as mp
import torch
import pickle
from collections import deque, Counter
import time
from train_proxy import GestureTransformer
import google.generativeai as genai
from googletrans import Translator
import pyttsx3
from gtts import gTTS
import os

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Set the GEMINI_API_KEY environment variable before running inference.")

genai.configure(api_key=api_key)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('voice', 'hi')  # Language hint; might fallback
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("⚠ pyttsx3 failed. Falling back to gTTS.")
        try:
            tts = gTTS(text=text, lang='hi')
            tts.save("output.mp3")
            os.system("start output.mp3")
        except Exception as e2:
            print(f"Text-to-speech failed: {e2}")

def process_and_speak(sentence):
    try:
        prompt = f"Correct the grammar of this sentence and return only the most suitable gramatically correct sentence: '{sentence}'"
        response = gemini_model.generate_content(prompt)
        corrected = response.text.strip().strip('"')
        print(f"[Corrected] {corrected}")

        translator = Translator()
        translated = translator.translate(corrected, src='en', dest='hi')
        hindi_text = translated.text
        print(f"[Hindi] {hindi_text}")

        speak_text(hindi_text)

    except Exception as err:
        print(f"Error: {err}")

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.3)
model = GestureTransformer()
model.load_state_dict(torch.load('gesture_transformer_proxy.pth'))
model.eval()
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
FEATURE_DIM = 126

# Load label map
with open('data_seq1.pickle', 'rb') as f:
    data_dict = pickle.load(f)

cap = cv2.VideoCapture(0)
sequence = []
predictions = deque(maxlen=90)

# Sentence building
collecting = False
sentence = []
last_added_word = ""
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (640, 340))
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    landmarks = []

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            for point in hand_landmarks.landmark:
                landmarks.extend([point.x, point.y, point.z])
        if len(results.multi_hand_landmarks) == 1:
            landmarks.extend([0] * (FEATURE_DIM - len(landmarks)))
    else:
        landmarks = [0] * FEATURE_DIM

    # Build sequence for model input
    sequence.append(landmarks)
    if len(sequence) > 30:
        sequence.pop(0)

    label_to_display = "Detecting..."

    if len(sequence) == 30:
        input_tensor = torch.tensor([sequence], dtype=torch.float32).to(device)
        input_tensor = input_tensor / torch.abs(input_tensor).max()
        with torch.no_grad():
            output = model(input_tensor)
            pred = torch.argmax(output, dim=1).item()
            label = data_dict['label_map'][pred]
            predictions.append(label)

        if collecting:
            most_common_label, count = Counter(predictions).most_common(1)[0]
            if count > 60 and most_common_label != last_added_word:
                sentence.append(most_common_label)
                last_added_word = most_common_label
                predictions.clear()

        label_to_display = label if results.multi_hand_landmarks else "Detecting..."

    cv2.putText(frame, label_to_display, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    if collecting:
        cv2.putText(frame, "Sentence: " + " ".join(sentence), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    else:
        if sentence:
            cv2.putText(frame, "Final Sentence: " + " ".join(sentence), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.imshow('Sign Language Recognition', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        print("[INFO] Started sentence collection")
        collecting = True
        sentence = []
        last_added_word = ""
        predictions.clear()
    elif key == ord('e'):
        print("Final Sentence:", " ".join(sentence))
        final_sentence = " ".join(sentence)
        process_and_speak(final_sentence)
        sentence.clear()

cap.release()
cv2.destroyAllWindows()

# Report
# Integration - Done
# PPT
# New Model using Transfer Learning
