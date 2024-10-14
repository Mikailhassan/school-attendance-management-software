from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from enum import Enum
import math
from dataclasses import dataclass

# Import your fingerprint models and database session
# from app.utils.fingerprint import get_fingerprint_scanner, FingerprintScanner
from app.models.fingerprint import Fingerprint
from app.database import get_db

@dataclass
class SecurityLevel:
    threshold_multiplier: float
    min_matching_points: int
    max_false_accept_rate: float
    max_false_reject_rate: float

class SecurityRequirement(Enum):
    LOW = SecurityLevel(0.8, 3, 0.001, 0.01)      # 0.1% FAR, 1% FRR
    MEDIUM = SecurityLevel(1.0, 5, 0.0001, 0.05)  # 0.01% FAR, 5% FRR
    HIGH = SecurityLevel(1.2, 7, 0.00001, 0.1)    # 0.001% FAR, 10% FRR

@dataclass
class ScannerCharacteristics:
    dpi: int
    scan_area: Tuple[int, int]  # width, height in pixels
    image_quality: int  # 0-100
    noise_level: float  # 0-1

class ThresholdCalculator:
    def __init__(self, security_level: SecurityRequirement):
        self.security_level = security_level
        self.historical_data: Dict[str, List[float]] = {
            'false_accepts': [],
            'false_rejects': [],
            'match_scores': []
        }
        self.scanner_characteristics = self._get_scanner_characteristics()
        self.last_adjustment = datetime.now()
        self.adjustment_interval = timedelta(hours=24)

    def _get_scanner_characteristics(self) -> ScannerCharacteristics:
        """Get the characteristics of the current scanner."""
        return ScannerCharacteristics(
            dpi=500,
            scan_area=(400, 400),
            image_quality=85,
            noise_level=0.15
        )

    def calculate_dynamic_threshold(self, current_match_score: float) -> int:
        """Calculate the dynamic threshold based on various factors."""
        self.historical_data['match_scores'].append(current_match_score)

        base_threshold = self.security_level.value.min_matching_points
        scanner_quality = self._calculate_scanner_quality()
        performance_factor = self._calculate_performance_factor()
        environmental_factor = self._calculate_environmental_factor()

        dynamic_threshold = math.ceil(
            base_threshold * 
            scanner_quality * 
            performance_factor * 
            environmental_factor *
            self.security_level.value.threshold_multiplier
        )
        
        logging.info(f"Threshold Calculation: Base: {base_threshold}, Scanner Quality: {scanner_quality:.2f}, "
                     f"Performance Factor: {performance_factor:.2f}, Environmental Factor: {environmental_factor:.2f}, "
                     f"Final Threshold: {dynamic_threshold}")
        
        return dynamic_threshold

    def _calculate_scanner_quality(self) -> float:
        """Calculate quality factor based on scanner characteristics."""
        dpi_factor = self.scanner_characteristics.dpi / 500
        quality_factor = self.scanner_characteristics.image_quality / 100
        noise_factor = 1 - self.scanner_characteristics.noise_level

        scanner_quality = (0.4 * dpi_factor + 0.4 * quality_factor + 0.2 * noise_factor)
        return 0.8 + (scanner_quality * 0.4)

    def _calculate_performance_factor(self) -> float:
        """Calculate performance factor based on historical FAR/FRR."""
        if not self.historical_data['match_scores']:
            logging.warning("No match scores available, using default performance factor of 1.0")
            return 1.0

        current_far = len(self.historical_data['false_accepts']) / max(len(self.historical_data['match_scores']), 1)
        current_frr = len(self.historical_data['false_rejects']) / max(len(self.historical_data['match_scores']), 1)

        far_ratio = current_far / self.security_level.value.max_false_accept_rate
        frr_ratio = current_frr / self.security_level.value.max_false_reject_rate

        performance_factor = 1.0 + (far_ratio - frr_ratio) * 0.1
        return max(0.9, min(1.1, performance_factor))

    def _calculate_environmental_factor(self) -> float:
        """Calculate environmental factor based on current conditions."""
        temperature = 22  # Celsius
        humidity = 50    # Percent
        
        temp_factor = 1.0 - abs(temperature - 22.5) / 50
        humidity_factor = 1.0 - abs(humidity - 50) / 100
        
        environmental_factor = (temp_factor + humidity_factor) / 2
        return 0.95 + (environmental_factor * 0.1)

    def update_historical_data(self, match_result: bool, expected_result: bool, match_score: float) -> None:
        """Update historical data with new matching results."""
        if match_result != expected_result:
            if match_result and not expected_result:
                self.historical_data['false_accepts'].append(match_score)
            else:
                self.historical_data['false_rejects'].append(match_score)

        max_history = 1000
        for key in self.historical_data:
            self.historical_data[key] = self.historical_data[key][-max_history:]

class FingerprintService:
    def __init__(self, db: Session = Depends(get_db)):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.scanner = None  # Initialize scanner as None to avoid immediate initialization
        self.threshold_calculator = ThresholdCalculator(SecurityRequirement.MEDIUM)

    def _initialize_scanner(self):
        """Initialize the fingerprint scanner when needed."""
        if self.scanner is None:
            try:
                # Uncomment the line below after setting up the actual scanner utility
                # self.scanner = get_fingerprint_scanner("digitalpersona")
                self.scanner.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize fingerprint scanner: {str(e)}")
                raise HTTPException(status_code=500, detail="Fingerprint scanner initialization failed")

    async def capture_fingerprint(self, user_id: str) -> None:
        """Capture a fingerprint and save it to the database."""
        self._initialize_scanner()  # Initialize scanner only when capturing a fingerprint
        try:
            fingerprint_data = await self.scanner.capture()
            new_fingerprint = Fingerprint(user_id=user_id, data=fingerprint_data)
            self.db.add(new_fingerprint)
            await self.db.commit()
            self.logger.info(f"Fingerprint captured and saved for user {user_id}.")
        except Exception as e:
            self.logger.error(f"Failed to capture fingerprint for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint capture failed")

    async def match_fingerprint(self, user_id: str, fingerprint_data: bytes) -> bool:
        """Match a fingerprint against the stored fingerprint for a user."""
        self._initialize_scanner()  # Initialize scanner when matching a fingerprint
        try:
            stored_fingerprint = await self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first()
            if not stored_fingerprint:
                self.logger.warning(f"No fingerprint found for user {user_id}.")
                return False
            
            match_score = await self.scanner.match(stored_fingerprint.data, fingerprint_data)
            threshold = self._get_matching_threshold()
            match_result = match_score >= threshold
            
            self.threshold_calculator.update_historical_data(match_result, True, match_score)
            
            self.logger.info(f"Fingerprint match result for user {user_id}: {match_result}. Score: {match_score}.")
            return match_result
            
        except Exception as e:
            self.logger.error(f"Failed to match fingerprint for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Fingerprint matching failed")

    def _get_matching_threshold(self) -> int:
        """Get the dynamic threshold for fingerprint matching."""
        try:
            recent_scores = self.threshold_calculator.historical_data['match_scores']
            current_score = recent_scores[-1] if recent_scores else 0.5
            
            threshold = self.threshold_calculator.calculate_dynamic_threshold(current_score)
            
            self.logger.info(f"Dynamic threshold calculated: {threshold}")
            return threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic threshold: {str(e)}")
            return SecurityRequirement.MEDIUM.value.min_matching_points

    async def delete_fingerprint(self, user_id: str) -> None:
        """Delete the fingerprint record for a user."""
        try:
            stored_fingerprint = await self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first()
            if not stored_fingerprint:
                self.logger.warning(f"No fingerprint found for user {user_id}. Cannot delete.")
                raise HTTPException(status_code=404, detail="Fingerprint not found.")

            await self.db.delete(stored_fingerprint)
            await self.db.commit()
            self.logger.info(f"Fingerprint deleted for user {user_id}.")
        except Exception as e:
            self.logger.error(f"Failed to delete fingerprint for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete fingerprint.")


    async def list_fingerprints(self) -> List[Dict[str, str]]:
        """List all fingerprints stored in the database."""
        try:
            fingerprints = await self.db.query(Fingerprint).all()
            return [{"user_id": fp.user_id, "data": fp.data} for fp in fingerprints]
        except Exception as e:
            self.logger.error(f"Failed to list fingerprints: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve fingerprints")
