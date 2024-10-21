import asyncio
from abc import ABC, abstractmethod
import numpy as np
from PIL import Image
import cv2
from fastapi import HTTPException
import logging
from typing import List, Tuple, Dict, Any
import skimage.morphology as morph
from scipy import ndimage, signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FingerprintScanner(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def capture(self) -> np.ndarray:
        pass

    @abstractmethod
    async def match(self, template1: np.ndarray, template2: np.ndarray) -> float:
        pass

class SupremaScanner(FingerprintScanner):
    def __init__(self):
        self.device = None
        self.initialized = False

    async def initialize(self) -> None:
        if self.initialized:
            return
            
        try:
            # Note: Commented out as pysupremafp might not be available
            # self.device = pysupremafp.SupremaDevice()
            # await asyncio.to_thread(self.device.open)
            self.initialized = True
            logging.info("Suprema scanner initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Suprema scanner: {str(e)}")
            raise HTTPException(status_code=500, detail="Scanner initialization failed")

    async def capture(self) -> np.ndarray:
        if not self.initialized:
            await self.initialize()
            
        try:
            # For testing without actual hardware:
            # Create a dummy fingerprint image
            dummy_image = np.random.randint(0, 256, (500, 500), dtype=np.uint8)
            return dummy_image
            
            # With actual hardware:
            # raw_image = await asyncio.to_thread(self.device.capture_image)
            # return self._preprocess_image(raw_image)
        except Exception as e:
            logging.error(f"Failed to capture fingerprint: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint capture failed")

    async def match(self, template1: np.ndarray, template2: np.ndarray) -> float:
        if not self.initialized:
            await self.initialize()
            
        try:
            # Implement matching logic here
            # For testing, return a random score between 0 and 1
            return np.random.random()
            
            # With actual hardware:
            # score = await asyncio.to_thread(self.device.match_templates, template1, template2)
            # return score
        except Exception as e:
            logging.error(f"Failed to match fingerprints: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint matching failed")

    def _preprocess_image(self, raw_image: bytes) -> np.ndarray:
        try:
            img = Image.frombytes('L', (500, 500), raw_image)
            img_array = np.array(img)
            return img_array
        except Exception as e:
            logging.error(f"Failed to preprocess image: {str(e)}")
            raise HTTPException(status_code=500, detail="Image preprocessing failed")

class ZKTecoScanner(FingerprintScanner):
    # Implement ZKTeco scanner class similarly to SupremaScanner
    pass

class DigitalPersonaScanner(FingerprintScanner):
    # Implement Digital Persona scanner class similarly to SupremaScanner
    pass

async def enhance_fingerprint(image: np.ndarray) -> np.ndarray:
    """Enhance the fingerprint image using various techniques."""
    try:
        # Convert to 8-bit grayscale if not already
        if image.dtype != np.uint8:
            image = (image * 255).astype(np.uint8)
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(image)
        
        # Noise reduction
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Enhance contrast
        enhanced = cv2.equalizeHist(enhanced)
        
        # Sharpen the image
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        enhanced = cv2.filter2D(enhanced, -1, kernel)
        
        return enhanced
    except Exception as e:
        logging.error(f"Failed to enhance fingerprint image: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint enhancement failed")

def segment_fingerprint(image: np.ndarray) -> np.ndarray:
    """Segment the fingerprint from the background."""
    try:
        # Normalize the image
        normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            normalized, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 
            11, 
            2
        )
        
        # Clean up noise
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Find the largest connected component
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, 4)
        
        # Find the largest non-background component
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        
        # Create mask of largest component
        mask = np.zeros_like(image)
        mask[labels == largest_label] = 255
        
        # Apply mask to original image
        segmented = cv2.bitwise_and(image, image, mask=mask)
        
        return segmented
    except Exception as e:
        logging.error(f"Failed to segment fingerprint: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint segmentation failed")

def assess_fingerprint_quality(image: np.ndarray) -> float:
    """Assess the quality of the fingerprint image."""
    try:
        # Calculate image contrast
        contrast = np.std(image) / 255.0
        
        # Calculate image sharpness
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        sharpness = np.var(laplacian) / (255.0 ** 2)
        
        # Calculate foreground-background ratio
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        foreground_ratio = np.sum(binary > 0) / binary.size
        
        # Calculate ridge clarity
        sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        ridge_clarity = np.mean(gradient_magnitude) / 255.0
        
        # Combine metrics
        weights = {
            'contrast': 0.25,
            'sharpness': 0.25,
            'foreground_ratio': 0.25,
            'ridge_clarity': 0.25
        }
        
        quality_score = (
            weights['contrast'] * contrast +
            weights['sharpness'] * sharpness +
            weights['foreground_ratio'] * foreground_ratio +
            weights['ridge_clarity'] * ridge_clarity
        )
        
        return min(max(quality_score, 0.0), 1.0)  # Ensure score is between 0 and 1
        
    except Exception as e:
        logging.error(f"Failed to assess fingerprint quality: {str(e)}")
        raise HTTPException(status_code=500, detail="Quality assessment failed")

def extract_minutiae(image: np.ndarray) -> List[Tuple[int, int, float]]:
    """Extract minutiae points from the fingerprint image."""
    try:
        # Binarize the image
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Thin the binary image
        thinned = morph.thin(binary > 0)
        
        # Convert to uint8
        thinned = thinned.astype(np.uint8) * 255
        
        minutiae = []
        
        # Crossing number method
        def get_crossing_number(values):
            return np.sum(np.abs(np.diff(values + [values[0]]))) // 2
        
        height, width = thinned.shape
        for i in range(1, height - 1):
            for j in range(1, width - 1):
                if thinned[i, j] == 255:  # Ridge pixel
                    # Get 8-neighborhood
                    values = [
                        thinned[i-1, j-1] // 255,
                        thinned[i-1, j] // 255,
                        thinned[i-1, j+1] // 255,
                        thinned[i, j+1] // 255,
                        thinned[i+1, j+1] // 255,
                        thinned[i+1, j] // 255,
                        thinned[i+1, j-1] // 255,
                        thinned[i, j-1] // 255
                    ]
                    
                    cn = get_crossing_number(values)
                    
                    if cn == 1:  # Ridge ending
                        minutiae.append((i, j, 0))
                    elif cn == 3:  # Ridge bifurcation
                        minutiae.append((i, j, 1))
        
        return minutiae
        
    except Exception as e:
        logging.error(f"Failed to extract minutiae: {str(e)}")
        raise HTTPException(status_code=500, detail="Minutiae extraction failed")

def create_fingerprint_template(
    image: np.ndarray, 
    minutiae: List[Tuple[int, int, float]]
) -> Dict[str, Any]:
    """Create a comprehensive fingerprint template."""
    try:
        template = {
            'image_size': image.shape,
            'minutiae': np.array(minutiae),
            'ridge_orientation': calculate_ridge_orientation(image),
            'ridge_frequency': estimate_ridge_frequency(image),
            'core_points': detect_core_points(image)
        }
        return template
    except Exception as e:
        logging.error(f"Failed to create template: {str(e)}")
        raise HTTPException(status_code=500, detail="Template creation failed")

def calculate_ridge_orientation(image: np.ndarray, block_size: int = 16) -> np.ndarray:
    """Calculate ridge orientation field."""
    try:
        # Calculate gradients
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        
        # Calculate gradient covariance
        gxx = gx * gx
        gyy = gy * gy
        gxy = gx * gy
        
        # Block processing
        height, width = image.shape
        orientation = np.zeros((height // block_size, width // block_size))
        
        for i in range(0, height - block_size, block_size):
            for j in range(0, width - block_size, block_size):
                gxx_block = gxx[i:i+block_size, j:j+block_size]
                gyy_block = gyy[i:i+block_size, j:j+block_size]
                gxy_block = gxy[i:i+block_size, j:j+block_size]
                
                # Calculate dominant direction
                orientation[i//block_size, j//block_size] = 0.5 * np.arctan2(
                    2 * np.sum(gxy_block),
                    np.sum(gxx_block - gyy_block)
                )
        
        return orientation
    except Exception as e:
        logging.error(f"Failed to calculate ridge orientation: {str(e)}")
        return np.zeros((image.shape[0]//16, image.shape[1]//16))

def estimate_ridge_frequency(image: np.ndarray, block_size: int = 16) -> np.ndarray:
    """Estimate ridge frequency in the fingerprint image."""
    try:
        # Calculate orientation field
        orientation = calculate_ridge_orientation(image, block_size)
        
        height, width = image.shape
        frequency = np.zeros((height // block_size, width // block_size))
        
        for i in range(0, height - block_size, block_size):
            for j in range(0, width - block_size, block_size):
                block = image[i:i+block_size, j:j+block_size]
                angle = orientation[i//block_size, j//block_size]
                
                # Rotate block to align ridges vertically
                rotated = ndimage.rotate(block, angle * 180 / np.pi - 90, reshape=False)
                
                # Project along columns
                projection = np.sum(rotated, axis=1)
                
                # Find peaks
                peaks, _ = signal.find_peaks(projection)
                
                if len(peaks) >= 2:
                    # Calculate frequency from average peak distance
                    frequency[i//block_size, j//block_size] = len(peaks) / block_size
        
        return frequency
    except Exception as e:
        logging.error(f"Failed to estimate ridge frequency: {str(e)}")
        return np.zeros((image.shape[0]//16, image.shape[1]//16))

def detect_core_points(image: np.ndarray) -> List[Tuple[int, int]]:
    """Detect core points in the fingerprint."""
    try:
        # Calculate orientation field
        orientation = calculate_ridge_orientation(image)
        
        # Calculate Poincare index
        core_points = []
        height, width = orientation.shape
        
        for i in range(1, height - 1):
            for j in range(1, width - 1):
                # Get orientation values in 2x2 neighborhood
                angles = [orientation[i-1, j-1],
                    orientation[i-1, j],
                    orientation[i, j],
                    orientation[i, j-1]
                ]
                
                # Calculate Poincare index
                index = sum(np.diff([*angles, angles[0]]))
                
                if abs(index) > np.pi:  # Core point detected
                    core_points.append((i * 16, j * 16))  # Scale back to image coordinates
        
        return core_points
    except Exception as e:
        logging.error(f"Failed to detect core points: {str(e)}")
        return []

async def process_fingerprint(scanner: FingerprintScanner) -> Dict[str, Any]:
    """Process a fingerprint from the scanner."""
    try:
        # Capture the fingerprint
        raw_image = await scanner.capture()

        # Enhance the fingerprint image
        enhanced_image = await enhance_fingerprint(raw_image)

        # Segment the fingerprint from the background
        segmented_image = segment_fingerprint(enhanced_image)

        # Assess the quality of the fingerprint
        quality_score = assess_fingerprint_quality(segmented_image)
        if quality_score < 0.5:  # Threshold can be adjusted based on testing
            raise HTTPException(status_code=400, detail="Fingerprint quality is too low for processing")

        # Extract minutiae points
        minutiae = extract_minutiae(segmented_image)

        # Create a fingerprint template
        template = create_fingerprint_template(segmented_image, minutiae)

        return {
            "raw_image": raw_image,
            "enhanced_image": enhanced_image,
            "segmented_image": segmented_image,
            "quality_score": quality_score,
            "template": template
        }
    except HTTPException as e:
        logging.error(f"Fingerprint processing error: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during fingerprint processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint processing failed")