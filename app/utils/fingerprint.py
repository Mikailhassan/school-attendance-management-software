from abc import ABC, abstractmethod
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import numpy as np
from dataclasses import dataclass
import cv2
import fprint
from scipy import ndimage

class FingerprintScanner(ABC):
    @abstractmethod
    def capture_fingerprint(self) -> np.ndarray:
        pass

    @abstractmethod
    def extract_features(self, fingerprint_image: np.ndarray) -> Any:
        pass

    @abstractmethod
    def compare_fingerprints(self, fingerprint1: Any, fingerprint2: Any) -> bool:
        pass

class RidgeOrientationFieldEstimator:
    def __init__(self, block_size: int = 16):
        self.block_size = block_size

    def estimate(self, image: np.ndarray) -> np.ndarray:
        logging.info("Estimating ridge orientation field.")
        gradients_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gradients_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        orientations = np.arctan2(gradients_y, gradients_x) / 2
        return orientations

class FrequencyEstimator:
    def __init__(self, block_size: int = 16):
        self.block_size = block_size

    def _calculate_ridge_frequency(self, block: np.ndarray) -> float:
        logging.debug("Calculating ridge frequency.")
        return np.mean(block)

    def assess_ridge_frequency(self, image: np.ndarray, orientation_field: np.ndarray) -> np.ndarray:
        height, width = image.shape
        freq_map = np.zeros((height, width))

        for i in range(0, height, self.block_size):
            for j in range(0, width, self.block_size):
                block = image[i:i+self.block_size, j:j+self.block_size]
                orientation_block = orientation_field[i:i+self.block_size, j:j+self.block_size]
                ridge_freq = self._calculate_ridge_frequency(block)
                freq_map[i:i+self.block_size, j:j+self.block_size] = ridge_freq

        return freq_map

class ContinuityAssessor:
    def assess(self, orientation_field: np.ndarray) -> float:
        logging.info("Assessing ridge continuity.")
        return np.var(orientation_field)

class MinutiaeExtractor:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def _detect_minutiae(self, image: np.ndarray) -> List[Tuple[int, int]]:
        logging.info("Detecting minutiae.")
        minutiae_points = []
        skeleton = cv2.ximgproc.thinning(image)
        for i in range(1, skeleton.shape[0] - 1):
            for j in range(1, skeleton.shape[1] - 1):
                if skeleton[i, j] == 1:
                    surrounding_sum = np.sum(skeleton[i-1:i+2, j-1:j+2]) - skeleton[i, j]
                    if surrounding_sum == 1 or surrounding_sum == 3:
                        minutiae_points.append((i, j))

        return minutiae_points

    def extract(self, image: np.ndarray) -> List[Tuple[int, int]]:
        logging.info("Extracting minutiae from fingerprint image.")
        return self._detect_minutiae(image)

class FingerprintService(FingerprintScanner):
    def __init__(self, device: fprint.FprintDevice):
        self.device = device

    def capture_fingerprint(self) -> np.ndarray:
        logging.info("Capturing fingerprint using device.")
        return self.device.capture_fingerprint()

    def extract_features(self, fingerprint_image: np.ndarray) -> Dict[str, Any]:
        logging.info("Extracting fingerprint features.")
        orientation_estimator = RidgeOrientationFieldEstimator()
        frequency_estimator = FrequencyEstimator()
        continuity_assessor = ContinuityAssessor()
        minutiae_extractor = MinutiaeExtractor()

        orientation_field = orientation_estimator.estimate(fingerprint_image)
        frequency_map = frequency_estimator.assess_ridge_frequency(fingerprint_image, orientation_field)
        continuity_score = continuity_assessor.assess(orientation_field)
        minutiae_points = minutiae_extractor.extract(fingerprint_image)

        return {
            "orientation_field": orientation_field,
            "frequency_map": frequency_map,
            "continuity_score": continuity_score,
            "minutiae_points": minutiae_points
        }

    def compare_fingerprints(self, fingerprint1: Dict[str, Any], fingerprint2: Dict[str, Any]) -> bool:
        logging.info("Comparing fingerprints.")
        orientation_similarity = np.mean(fingerprint1['orientation_field'] == fingerprint2['orientation_field'])
        frequency_similarity = np.mean(fingerprint1['frequency_map'] == fingerprint2['frequency_map'])
        minutiae_similarity = len(set(fingerprint1['minutiae_points']) & set(fingerprint2['minutiae_points']))

        logging.debug(f"Orientation similarity: {orientation_similarity}")
        logging.debug(f"Frequency similarity: {frequency_similarity}")
        logging.debug(f"Minutiae similarity: {minutiae_similarity}")

        return orientation_similarity > 0.9 and frequency_similarity > 0.9 and minutiae_similarity > 5

class FingerprintMatcher:
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def match(self, fingerprint1: Dict[str, Any], fingerprint2: Dict[str, Any]) -> bool:
        logging.info("Matching two fingerprints.")
        orientation_similarity = np.mean(fingerprint1['orientation_field'] == fingerprint2['orientation_field'])
        frequency_similarity = np.mean(fingerprint1['frequency_map'] == fingerprint2['frequency_map'])
        minutiae_similarity = len(set(fingerprint1['minutiae_points']) & set(fingerprint2['minutiae_points']))

        logging.debug(f"Orientation similarity: {orientation_similarity}")
        logging.debug(f"Frequency similarity: {frequency_similarity}")
        logging.debug(f"Minutiae similarity: {minutiae_similarity}")

        score = (orientation_similarity + frequency_similarity + minutiae_similarity / len(fingerprint1['minutiae_points'])) / 3
        logging.info(f"Matching score: {score}")

        return score >= self.threshold

@dataclass
class FingerprintTemplate:
    minutiae_points: List[Tuple[int, int]]
    orientation_field: np.ndarray
    frequency_map: np.ndarray

class FingerprintTemplateDatabase:
    def __init__(self):
        self.templates: Dict[int, FingerprintTemplate] = {}

    def add_template(self, user_id: int, template: FingerprintTemplate):
        logging.info(f"Adding fingerprint template for user {user_id}.")
        self.templates[user_id] = template

    def get_template(self, user_id: int) -> Optional[FingerprintTemplate]:
        logging.info(f"Retrieving fingerprint template for user {user_id}.")
        return self.templates.get(user_id)

    def remove_template(self, user_id: int):
        logging.info(f"Removing fingerprint template for user {user_id}.")
        if user_id in self.templates:
            del self.templates[user_id]

class FingerprintVerificationService:
    def __init__(self, scanner: FingerprintScanner, database: FingerprintTemplateDatabase, matcher: FingerprintMatcher):
        self.scanner = scanner
        self.database = database
        self.matcher = matcher

    def enroll(self, user_id: int):
        logging.info(f"Enrolling user {user_id}.")
        fingerprint_image = self.scanner.capture_fingerprint()
        features = self.scanner.extract_features(fingerprint_image)
        template = FingerprintTemplate(
            minutiae_points=features['minutiae_points'],
            orientation_field=features['orientation_field'],
            frequency_map=features['frequency_map']
        )
        self.database.add_template(user_id, template)

    def verify(self, user_id: int) -> bool:
        logging.info(f"Verifying user {user_id}.")
        fingerprint_image = self.scanner.capture_fingerprint()
        extracted_features = self.scanner.extract_features(fingerprint_image)
        stored_template = self.database.get_template(user_id)

        if not stored_template:
            logging.warning(f"No template found for user {user_id}.")
            return False

        stored_features = {
            "minutiae_points": stored_template.minutiae_points,
            "orientation_field": stored_template.orientation_field,
            "frequency_map": stored_template.frequency_map
        }

        return self.matcher.match(extracted_features, stored_features)

# Additional methods (not included in the original classes)

def _calculate_ridge_frequency(self, thinned_img: np.ndarray) -> np.ndarray:
    logging.info("Calculating ridge frequency.")
    rows, cols = thinned_img.shape
    frequency_map = np.zeros((rows, cols))
    window_size = 16

    for i in range(0, rows - window_size, window_size):
        for j in range(0, cols - window_size, window_size):
            window = thinned_img[i:i + window_size, j:j + window_size]
            
            try:
                freq = self._perform_frequency_analysis(window)
                frequency_map[i:i + window_size, j:j + window_size] = freq
            except ValueError as e:
                logging.warning(f"Error in ridge frequency calculation: {e}")
                continue

    return frequency_map

def _perform_frequency_analysis(self, window: np.ndarray) -> float:
    fft_result = np.fft.fft2(window)
    magnitude_spectrum = np.abs(fft_result)
    frequency_peak = np.argmax(magnitude_spectrum)
    ridge_frequency = frequency_peak / len(magnitude_spectrum)
    return ridge_frequency

def _assess_ridge_continuity(self, img: np.ndarray) -> np.ndarray:
    logging.info("Assessing ridge continuity.")
    rows, cols = img.shape
    continuity_map = np.zeros((rows, cols))
    window_size = 16

    for i in range(0, rows - window_size, window_size):
        for j in range(0, cols - window_size, window_size):
            window = img[i:i + window_size, j:j + window_size]
            
            try:
                gradient_variance = self._calculate_gradient_variance(window)
                continuity_map[i:i + window_size, j:j + window_size] = gradient_variance
            except ValueError as e:
                logging.warning(f"Error assessing ridge continuity: {e}")
                continue

    return continuity_map

def _calculate_gradient_variance(self, window: np.ndarray) -> float:
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    grad_x = ndimage.convolve(window, sobel_x)
    grad_y = ndimage.convolve(window, sobel_y)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
    variance = np.var(magnitude)
    return variance

def _calculate_ridge_valley_separation(self, img: np.ndarray) -> np.ndarray:
    logging.info("Calculating ridge-valley separation.")
    rows, cols = img.shape
    separation_map = np.zeros((rows, cols))
    block_size = 16

    for i in range(0, rows - block_size, block_size):
        for j in range(0, cols - block_size, block_size):
            block = img[i:i + block_size, j:j + block_size]
            block_mean = np.mean(block)
            separation = np.where(block >= block_mean, 1, 0)
            separation_map[i:i + block_size, j:j + block_size] = separation

    return separation_map

def _calculate_poincare_index(self, orientation_field: np.ndarray) -> np.ndarray:
    logging.info("Calculating Poincare index for singularities detection.")
    rows, cols = orientation_field.shape
    poincare_map = np.zeros((rows, cols))
    block_size = 16

    for i in range(0, rows - block_size, block_size):
        for j in range(0, cols - block_size, block_size):
            block = orientation_field[i:i + block_size, j:j + block_size]

            try:
                poincare_index = self._calculate_local_poincare(block)
                poincare_map[i:i + block_size, j:j + block_size] = poincare_index
            except ValueError as e:
                logging.warning(f"Error calculating Poincare index: {e}")
                continue

    return poincare_map

def _calculate_local_poincare(self, block: np.ndarray) -> float:
    angle_diffs = np.diff(block, axis=0).sum() + np.diff(block, axis=1).sum()
    poincare_index = angle_diffs / (2 * np.pi)
    return poincare_index

def _enhance_ridges(self, img: np.ndarray) -> np.ndarray:
    logging.info("Enhancing ridges.")
    enhanced_img = cv2.GaussianBlur(img, (3, 3), 0)
    enhanced_img = cv2.equalizeHist(enhanced_img.astype(np.uint8))
    return enhanced_img

def _thin_image(self, img: np.ndarray) -> np.ndarray:
    logging.info("Thinning the fingerprint image.")
    thinned_img = cv2.ximgproc.thinning(img)
    return thinned_img

def _reduce_noise(self, img: np.ndarray) -> np.ndarray:
    logging.info("Reducing noise in the image.")
    reduced_noise_img = cv2.medianBlur(img, 3)
    return reduced_noise_img

def _align_fingerprint(self, img: np.ndarray) -> np.ndarray:
    logging.info("Aligning fingerprint image based on orientation.")
    orientation_field = self._compute_orientation_field(img)
    angle = self._get_dominant_orientation(orientation_field)
    rotated_img = ndimage.rotate(img, angle, reshape=False)
    return rotated_img

def _get_dominant_orientation(self, orientation_field: np.ndarray) -> float:
    dominant_orientation = np.mean(orientation_field)
    return dominant_orientation

def match_fingerprints(self, fingerprint1: np.ndarray, fingerprint2: np.ndarray) -> bool:
    logging.info("Matching two fingerprints.")
    fingerprint1_minutiae = self._detect_minutiae(fingerprint1)
    fingerprint2_minutiae = self._detect_minutiae(fingerprint2)
    similarity_score = self._compare_minutiae(fingerprint1_minutiae, fingerprint2_minutiae)
    match_threshold = 0.8
    if similarity_score > match_threshold:
        logging.info("Fingerprints matched successfully.")
        return True
    else:
        logging.info("Fingerprints did not match.")
        return False

def _compare_minutiae(self, minutiae1: List[Tuple[int, int]], minutiae2: List[Tuple[int, int]]) -> float:
    matched_points = 0
    for m1 in minutiae1:
        for m2 in minutiae2:
            if np.linalg.norm(np.array(m1) - np.array(m2)) < 10:
                matched_points += 1
    total_points = max(len(minutiae1), len(minutiae2))
    similarity_score = matched_points / total_points
    return similarity_score

def save_fingerprint_template(self, fingerprint_img: np.ndarray, user_id: str) -> bool:
    logging.info(f"Saving fingerprint template for user {user_id}.")
    minutiae = self._detect_minutiae(fingerprint_img)
    template_file = f"{user_id}_fingerprint_template.npy"
    np.save(template_file, minutiae)
    logging.info(f"Fingerprint template saved as {template_file}.")
    return True

def load_fingerprint_template(self, user_id: str) -> Optional[np.ndarray]:
    logging.info(f"Loading fingerprint template for user {user_id}.")
    template_file = f"{user_id}_fingerprint_template.npy"
    try:
        minutiae = np.load(template_file)
        logging.info(f"Fingerprint template loaded successfully from {template_file}.")
        return minutiae
    except FileNotFoundError:
        logging.error(f"Template file {template_file} not found.")
        return None

def enroll_fingerprint(self, fingerprint_img: np.ndarray, user_id: str) -> bool:
    logging.info(f"Enrolling fingerprint for user {user_id}.")
    enhanced_img = self._enhance_ridges(fingerprint_img)
    thinned_img = self._thin_image(enhanced_img)
    return self.save_fingerprint_template(thinned_img, user_id)

def verify_fingerprint(self, fingerprint_img: np.ndarray, user_id: str) -> bool:
    logging.info(f"Verifying fingerprint for user {user_id}.")
    enhanced_img = self._enhance_ridges(fingerprint_img)
    thinned_img = self._thin_image(enhanced_img)
    saved_template = self.load_fingerprint_template(user_id)
    if saved_template is None:
        logging.error("No saved template found for the user.")
        return False
    return self.match_fingerprints(thinned_img, saved_template)