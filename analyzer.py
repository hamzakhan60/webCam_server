import cv2
import numpy as np

# Load OpenCV models (Haar cascades)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

def analyze_frame(frame):
    try:
        print("Frame received")
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        print("Faces detected:", len(faces))
        # Draw face rectangles on original frame
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Region of interest for eyes
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)

            # Draw rectangles around eyes
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (255, 0, 0), 2)


        # Status logic
        if len(faces) == 0:
            return "AFK"
        elif len(eyes) >= 2:
            return "FOCUSED"
        else:
            return "PRESENT"

    except Exception as e:
        print("Error:", e)
        return "ERROR"
