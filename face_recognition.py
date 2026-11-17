import os
import re
import shutil

import cv2
import numpy as np
from PIL import Image


FACE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_faces")
FACE_SIZE = (160, 160)
MATCH_DISTANCE_LIMIT = 70.0


def _coerce_image(image):
    if image is None:
        raise ValueError("Capture or upload a photo first.")
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if hasattr(image, "read"):
        return Image.open(image).convert("RGB")
    return Image.fromarray(image).convert("RGB")


def _prepare_face(photo):
    image = _coerce_image(photo)
    rgb_image = np.asarray(image)
    gray_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    cascade_path = os.path.join(
        cv2.data.haarcascades, "haarcascade_frontalface_default.xml"
    )
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError(
            "OpenCV's face detector files are missing. Reinstall the project requirements."
        )

    faces = detector.detectMultiScale(
        gray_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    if len(faces) == 0:
        raise ValueError("No face detected. Use a clear, front-facing photo.")
    if len(faces) > 1:
        raise ValueError("Only one face should be visible in the photo.")

    x, y, width, height = faces[0]
    crop = gray_image[y : y + height, x : x + width]
    normalized = cv2.equalizeHist(crop)
    return cv2.resize(normalized, FACE_SIZE, interpolation=cv2.INTER_AREA)


def register_face_photo(roll_no, photo):
    roll_no = str(roll_no).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", roll_no):
        raise ValueError("Use letters, numbers, dots, underscores, or hyphens in roll numbers.")

    image_path = os.path.join(FACE_FOLDER, roll_no, "face.jpg")
    if os.path.exists(image_path):
        raise ValueError("A face photo already exists for this roll number.")

    face = _prepare_face(photo)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    if not cv2.imwrite(image_path, face):
        raise OSError("Could not save the face photo.")
    return image_path


def delete_face_profile(roll_no):
    student_folder = os.path.join(FACE_FOLDER, str(roll_no))
    if os.path.isdir(student_folder):
        shutil.rmtree(student_folder)


def recognize_face(photo):
    query_face = _prepare_face(photo)
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "OpenCV face recognition is missing. Install opencv-contrib-python-headless."
        )

    roll_numbers = []
    face_images = []
    if not os.path.isdir(FACE_FOLDER):
        return None

    for roll_no in sorted(os.listdir(FACE_FOLDER)):
        image_path = os.path.join(FACE_FOLDER, roll_no, "face.jpg")
        if not os.path.isfile(image_path):
            continue
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise RuntimeError(f"Could not read the saved face profile for {roll_no}.")
        face_images.append(cv2.resize(image, FACE_SIZE, interpolation=cv2.INTER_AREA))
        roll_numbers.append(roll_no)

    if not face_images:
        return None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    labels = np.arange(len(face_images), dtype=np.int32)
    recognizer.train(face_images, labels)
    label, distance = recognizer.predict(query_face)
    if distance > MATCH_DISTANCE_LIMIT:
        return None
    return roll_numbers[label]
