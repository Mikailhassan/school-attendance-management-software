import asyncio
from abc import ABC, abstractmethod
import numpy as np
from PIL import Image
import cv2
from fastapi import HTTPException
import logging
from typing import List, Tuple
import skimage.morphology as morph
from scipy import ndimage
import matplotlib.pyplot as plt

# You may need to install these libraries
# import pysupremafp
# pip install scikit-image scipy matplotlib

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

    async def initialize(self) -> None:
        try:
            self.device = pysupremafp.SupremaDevice()
            await asyncio.to_thread(self.device.open)
        except Exception as e:
            logging.error(f"Failed to initialize Suprema scanner: {str(e)}")
            raise HTTPException(status_code=500, detail="Scanner initialization failed")

    async def capture(self) -> np.ndarray:
        try:
            raw_image = await asyncio.to_thread(self.device.capture_image)
            return self._preprocess_image(raw_image)
        except Exception as e:
            logging.error(f"Failed to capture fingerprint with Suprema: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint capture failed")

    async def match(self, template1: np.ndarray, template2: np.ndarray) -> float:
        try:
            score = await asyncio.to_thread(self.device.match_templates, template1, template2)
            return score
        except Exception as e:
            logging.error(f"Failed to match fingerprints with Suprema: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint matching failed")

    def _preprocess_image(self, raw_image: bytes) -> np.ndarray:
        img = Image.frombytes('L', (500, 500), raw_image)  # Adjust size as needed
        img_array = np.array(img)
        return img_array

async def enhance_fingerprint(image: np.ndarray) -> np.ndarray:
    """Enhance the fingerprint image using various techniques."""
    try:
        # Convert to 8-bit grayscale if not already
        if image.dtype != np.uint8:
            image = (image * 255).astype(np.uint8)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(image)
        
        # Apply Gaussian blur to reduce noise
        enhanced = cv2.GaussianBlur(enhanced, (5, 5), 0)
        
        # Increase contrast
        enhanced = cv2.addWeighted(enhanced, 1.5, enhanced, -0.5, 0)
        
        return enhanced
    except Exception as e:
        logging.error(f"Failed to enhance fingerprint image: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint enhancement failed")

def segment_fingerprint(image: np.ndarray) -> np.ndarray:
    """Segment the fingerprint from the background."""
    try:
        # Apply threshold to separate foreground from background
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to clean up the segmentation
        kernel = np.ones((5,5), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Find sure background area
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Find sure foreground area
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.7*dist_transform.max(), 255, 0)
        
        # Find unknown region
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # Marker labelling
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown==255] = 0
        
        # Apply watershed algorithm
        markers = cv2.watershed(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), markers)
        
        # Create mask of segmented fingerprint
        mask = np.zeros(image.shape, dtype="uint8")
        mask[markers > 1] = 255
        
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
        contrast = np.std(image)
        
        # Calculate image sharpness
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        sharpness = np.var(laplacian)
        
        # Calculate ridge clarity (using Sobel edges)
        sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        edge_strength = np.sqrt(sobelx**2 + sobely**2)
        ridge_clarity = np.mean(edge_strength)
        
        # Combine metrics (you may want to adjust the weights)
        quality_score = (0.3 * contrast + 0.3 * sharpness + 0.4 * ridge_clarity) / 255
        
        return quality_score
    except Exception as e:
        logging.error(f"Failed to assess fingerprint quality: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint quality assessment failed")

def estimate_ridge_frequency(image: np.ndarray, block_size: int = 16) -> np.ndarray:
    """Estimate the ridge frequency of the fingerprint image."""
    try:
        # Normalize the image
        normalized = cv2.normalize(image, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        
        # Calculate gradients
        gy, gx = np.gradient(normalized)
        
        # Calculate orientation
        gxx = gx * gx
        gyy = gy * gy
        gxy = gx * gy
        
        height, width = image.shape
        orientation = np.zeros((height // block_size, width // block_size))
        frequency = np.zeros_like(orientation)
        
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                gxx_block = gxx[i:i+block_size, j:j+block_size]
                gyy_block = gyy[i:i+block_size, j:j+block_size]
                gxy_block = gxy[i:i+block_size, j:j+block_size]
                
                orientation[i//block_size, j//block_size] = 0.5 * np.arctan2(
                    2 * np.sum(gxy_block),
                    np.sum(gxx_block - gyy_block)
                )
                
                # Project gradients
                rotated = ndimage.rotate(normalized[i:i+block_size, j:j+block_size], 
                                         orientation[i//block_size, j//block_size] * 180 / np.pi,
                                         reshape=False)
                
                # Sum projected gradients
                projection = np.sum(rotated, axis=0)
                
                # Find peaks
                peaks, _ = find_peaks(projection)
                
                if len(peaks) >= 2:
                    frequency[i//block_size, j//block_size] = len(peaks) / (peaks[-1] - peaks[0])
        
        return frequency
    except Exception as e:
        logging.error(f"Failed to estimate ridge frequency: {str(e)}")
        raise HTTPException(status_code=500, detail="Ridge frequency estimation failed")

def extract_minutiae(image: np.ndarray) -> List[Tuple[int, int, float]]:
    """Extract minutiae points from the fingerprint image."""
    try:
        # Binarize the image
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Thin the binary image
        thinned = morph.thin(binary)
        
        # Find minutiae points
        minutiae = []
        
        def get_pixel(img, center, x, y):
            new_x = min(center[0] + x, img.shape[0] - 1)
            new_y = min(center[1] + y, img.shape[1] - 1)
            return img[new_x, new_y]

        for i in range(1, thinned.shape[0] - 1):
            for j in range(1, thinned.shape[1] - 1):
                if thinned[i, j] == 1:
                    P = [get_pixel(thinned, (i,j), x, y) for x, y in [
                        (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]]
                    if sum(P) == 1:
                        minutiae.append((i, j, 0))  # Endpoint
                    elif sum(P) == 3:
                        minutiae.append((i, j, 1))  # Bifurcation
        
        return minutiae
    except Exception as e:
        logging.error(f"Failed to extract minutiae: {str(e)}")
        raise HTTPException(status_code=500, detail="Minutiae extraction failed")

def create_fingerprint_template(image: np.ndarray, minutiae: List[Tuple[int, int, float]]) -> np.ndarray:
    """Create a fingerprint template from the image and extracted minutiae."""
    try:
        # This is a simplified template creation. In practice, you'd want to include more information
        # such as ridge orientation, frequency, etc.
        template = np.zeros((len(minutiae), 3), dtype=np.float32)
        for i, (x, y, minutia_type) in enumerate(minutiae):
            template[i] = [x, y, minutia_type]
        return template
    except Exception as e:
        logging.error(f"Failed to create fingerprint template: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint template creation failed")

async def process_fingerprint(scanner: SupremaScanner):
    """Process a fingerprint from the scanner."""
    try:
        raw_image = await scanner.capture()
        
        # Segment the fingerprint
        segmented_image = segment_fingerprint(raw_image)
        
        # Enhance the fingerprint image
        enhanced_image = await enhance_fingerprint(segmented_image)
        
        # Assess quality
        quality_score = assess_fingerprint_quality(enhanced_image)
        if quality_score < 0.5:  # Example threshold
            raise HTTPException(status_code=400, detail=f"Fingerprint quality is too low: {quality_score:.2f}")
        
        # Estimate ridge frequency
        frequency_image = estimate_ridge_frequency(enhanced_image)
        
        # Extract minutiae
        minutiae = extract_minutiae(enhanced_image)
        
        # Create template
        template = create_fingerprint_template(enhanced_image, minutiae)
        
        return {
            'enhanced_image': enhanced_image,
            'quality_score': quality_score,
            'frequency_image': frequency_image,
            'minutiae': minutiae,
            'template': template
        }
    except Exception as e:
        logging.error(f"Error processing fingerprint: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint processing failed")

async def match_fingerprints(scanner: SupremaScanner, template1: np.ndarray, template2: np.ndarray) -> float:
    """Match two fingerprint templates."""
    try:
        match_score = await scanner.match(template1, template2)
        return match_score
    except Exception as e:
        logging.error(f"Error matching fingerprints: {str(e)}")
        raise HTTPException(status_code=500, detail="Fingerprint matching failed")

# Visualization function for debugging and analysis
def visualize_fingerprint(image: np.ndarray, minutiae: List[Tuple[int, int, float]], title: str):
    plt.figure(figsize=(10, 10))
    plt.imshow(image, cmap='gray')
    for x, y, minutia_type in minutiae:
        if minutia_type == 0:  # Endpoint
            plt.plot(y, x, 'ro', markersize=5)
        else:  # Bifurcation
            plt.plot(y, x, 'bo', markersize=5)
    plt.title(title)
    plt.axis('off')
    plt.show()

# Usage example
async def main():
    scanner = SupremaScanner()
    await scanner.initialize()
    
    # Process first fingerprint
    print("Place your finger on the scanner for the first scan...")
    result1 = await process_fingerprint(scanner)
    
    print(f"First fingerprint processed. Quality score: {result1['quality_score']:.2f}")
    visualize_fingerprint(result1['enhanced_image'], result1['minutiae'], "First Fingerprint")
    
    # Process second fingerprint
    print("Place your finger on the scanner for the second scan...")
    result2 = await process_fingerprint(scanner)
    
    print(f"Second fingerprint processed. Quality score: {result2['quality_score']:.2f}")
    visualize_fingerprint(result2['enhanced_image'], result2['minutiae'], "Second Fingerprint")
    
    # Match fingerprints
    match_score = await match_fingerprints(scanner, result1['template'], result2['template'])
    print(f"Match score: {match_score:.2f}")
