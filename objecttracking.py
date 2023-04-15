#!/usr/bin/env python
import cv2
import sys
import time
import os
from pantilthat import *
import RPi.GPIO as GPIO

os.system('sudo modprobe bcm2835-v4l2')
os.system('v4l2-ctl -p 40')

FRAME_W = 320
FRAME_H = 200
cam_pan = 40
cam_tilt = 20

# Set up GPIO for HC-SR04
GPIO.setmode(GPIO.BOARD)
TRIG_PIN = 11
ECHO_PIN = 12
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Function to measure distance using HC-SR04
def measure_distance():
    # Trigger the HC-SR04 to measure distance
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    # Wait for echo to be received
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()

    # Calculate distance from the duration of echo pulse
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    return distance

# Initialize pantilthat
pan(cam_pan-90)
tilt(cam_tilt-90)
light_mode(WS2812)

# Set initial state for following
follow_state = False

def lights(r, g, b, w):
    for x in range(18):
        set_pixel_rgbw(x, r if x in [3, 4] else 0, g if x in [3, 4] else 0, b, w if x in [0, 1, 6, 7] else 0)
    show()

lights(0, 0, 0, 50)

# Set up video capture
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 200)
time.sleep(2)

# Load Haar cascade classifier for face detection
cascPath = '/usr/share/opencv/lbpcascades/lbpcascade_frontalface.xml'
faceCascade = cv2.CascadeClassifier(cascPath)

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, -1)

    if ret == False:
        print("Error getting image")
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = faceCascade.detectMultiScale(frame, 1.1, 3, 0, (10, 10))

    lights(50 if len(faces) == 0 else 0, 50 if len(faces) > 0 else 0, 0, 50)

    # Measure distance using HC-SR04
    distance = measure_distance()

    # If face detected and distance is within a certain threshold, start following
    if len(faces) > 0 and distance < 50:
        follow_state = True
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 4)

            x = x + w // 2
            y = y + h // 2
            
            # Calculate pan and tilt angles based on face position
            pan_angle = (x / FRAME_W) * 180 - 90
            tilt_angle = (y / FRAME_H) * 180 - 90

            # Move pantilthat to follow the face
            pan(pan_angle)
            tilt(tilt_angle)

            # Update servo angles for future reference
            cam_pan = pan_angle
            cam_tilt = tilt_angle

    else:
        # If no face detected or distance is too far, stop following
        follow_state = False

    # If follow state is True, start following the person using servos
    if follow_state:
        # Calculate the pan and tilt angles based on the distance
        pan_angle = (cam_pan + (FRAME_W // 2 - x) / FRAME_W * 180) % 180 - 90
        tilt_angle = (cam_tilt + (FRAME_H // 2 - y) / FRAME_H * 180) % 180 - 90

        # Move pantilthat to follow the person
        pan(pan_angle)
        tilt(tilt_angle)

    # Display the video frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    # Exit the loop when 'q' is pressed
    if key == ord("q"):
        break
    
    # Release VideoCapture and destroy windows
    cap.release()
    cv2.destroyAllWindows()
    
    # Clean up GPIO
    GPIO.cleanup()

    
