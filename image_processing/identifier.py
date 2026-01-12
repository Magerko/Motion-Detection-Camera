import cv2
import numpy as np
import mediapipe as mp


class ObjectIdentifier:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_face = mp.solutions.face_detection
        try:
            self.pose_detector = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.face_detector = self.mp_face.FaceDetection(
                model_selection=1,
                min_detection_confidence=0.5
            )
        except Exception as e:
            print(f"Ошибка инициализации MediaPipe: {e}. Убедитесь, что mediapipe установлен корректно.")
            self.pose_detector = None
            self.face_detector = None

        self.person_label = "человек"
        self.unknown_label = "движение"

    def identify_objects(self, image_path=None, frame_data=None):
        if not self.pose_detector:
            return ["ошибка инициализации MediaPipe"]

        if frame_data is not None:
            frame = frame_data
        elif image_path is not None:
            frame = cv2.imread(image_path)
        else:
            return ["аргументы не предоставлены"]

        if frame is None:
            return ["ошибка кадра"]

        identified = []

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False

        pose_results = self.pose_detector.process(image_rgb)
        if pose_results.pose_landmarks:
            identified.append(self.person_label)

        if not identified and self.face_detector:
            face_results = self.face_detector.process(image_rgb)
            if face_results.detections:
                identified.append(self.person_label)

        if not identified:
            identified.append(self.unknown_label)

        return identified

    def close(self):
        if self.pose_detector:
            self.pose_detector.close()
        if self.face_detector:
            self.face_detector.close()
