import cv2
import numpy as np

try:
    import mediapipe as mp
    if hasattr(mp, 'solutions'):
        _mp_face = mp.solutions.face_detection
        MEDIAPIPE_AVAILABLE = True
    else:
        MEDIAPIPE_AVAILABLE = False
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class ObjectIdentifier:
    def __init__(self):
        self.person_label = "человек"
        self.unknown_label = "движение"
        self.detector = None

        if MEDIAPIPE_AVAILABLE:
            try:
                self.detector = _mp_face.FaceDetection(
                    model_selection=1,
                    min_detection_confidence=0.5
                )
            except Exception as e:
                print(f"Ошибка инициализации MediaPipe: {e}")

    def identify_objects(self, image_path=None, frame_data=None):
        if frame_data is not None:
            frame = frame_data
        elif image_path is not None:
            frame = cv2.imread(image_path)
        else:
            return [self.unknown_label]

        if frame is None or not self.detector:
            return [self.unknown_label]

        try:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.detector.process(image_rgb)
            if results.detections:
                return [self.person_label]
        except Exception:
            pass

        return [self.unknown_label]

    def close(self):
        if self.detector and hasattr(self.detector, 'close'):
            self.detector.close()
