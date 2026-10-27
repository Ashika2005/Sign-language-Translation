import os
import cv2
import time

# This script collects images from the webcam for a sign language dataset.
DATA_DIR = 'SignToTextConversion\SignToText\Data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

labels = ['Accident', 'Day', 'Good', 'Hello', 'How', 'Lose', 'Pain', 'You', 'Thank You']
num = 15
dataset_size = 100

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

for label in range(num):
    class_dir = os.path.join(DATA_DIR, str(labels[label]))
    os.makedirs(class_dir, exist_ok=True)

    print(f'Collecting data for class: {str(labels[label])}')

    # Wait for user to press 'q' before starting
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image")
            break

        # cv2.putText(where to display the message, 'message', position, font, font scale, color(BGR), thickness, line type)
        cv2.putText(frame, 'Press "Q" to start!', (100, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('frame', frame)

        # waitkey(1) waits for 1 ms and 0xFF means to check if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("Starting in 3 seconds...")
    time.sleep(3)  # Countdown before capturing starts

    counter = 100
    while counter < dataset_size:
        # cap.read() captures a frame from the webcam and returns a boolean indicating success and the frame itself
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image")
            break

        frame = cv2.resize(frame, (640, 640))  # Resize to a fixed input size
        cv2.imshow('frame', frame)
        cv2.imwrite(os.path.join(class_dir, f'{counter}.jpg'), frame)

        counter += 1
        if cv2.waitKey(1) & 0xFF == ord('e'):  # Option to exit early
            break

cap.release()
cv2.destroyAllWindows()
