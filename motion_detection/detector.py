# motion_detection/detector.py
import cv2
import numpy as np
import time
import os
from datetime import datetime


class MotionDetector:
    def __init__(self, min_area=1000, frame_width=640, frame_height=480):
        self.min_area = min_area
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cap = None
        self.previous_frame = None
        self.is_running = False
        self.video_writer = None
        self.video_filename = None

    def start_capture(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.previous_frame = self._get_processed_frame()
        self.is_running = True
        return True

    def _get_processed_frame(self):
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        return gray_blurred

    def detect_motion(self):
        if not self.is_running or self.previous_frame is None:
            return None

        ret, original_frame = self.cap.read()
        if not ret:
            return None

        current_processed_frame = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
        current_processed_frame = cv2.GaussianBlur(current_processed_frame, (21, 21), 0)

        frame_delta = cv2.absdiff(self.previous_frame, current_processed_frame)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self.previous_frame = current_processed_frame

        motion_detected_this_frame = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area:
                motion_detected_this_frame = True
                break

        if motion_detected_this_frame:
            return original_frame
        return None

    def capture_screenshot(self, frame, directory="screenshots"):
        if not os.path.exists(directory):
            os.makedirs(directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(directory, f"motion_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        return filename

    def start_video_recording(self, directory="motion_videos", fps=10):
        if not os.path.exists(directory):
            os.makedirs(directory)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = os.path.join(directory, f"video_{timestamp}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # или 'XVID' для .avi
        self.video_writer = cv2.VideoWriter(self.video_filename, fourcc, fps, (self.frame_width, self.frame_height))
        if self.video_writer.isOpened():
            return self.video_filename
        else:
            self.video_writer = None
            self.video_filename = None
            return None

    def write_video_frame(self, frame):
        if self.video_writer and self.video_writer.isOpened():
            self.video_writer.write(frame)
            return True
        return False

    def stop_video_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            return self.video_filename
        return None

    def stop_capture(self):
        if self.video_writer:
            self.stop_video_recording()
        if self.cap:
            self.cap.release()
        self.is_running = False
        self.previous_frame = None
