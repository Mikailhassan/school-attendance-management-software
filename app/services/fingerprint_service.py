from typing import List, Optional, Dict, Tuple
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.utils.fingerprint import get_fingerprint_scanner, FingerprintScanner
from app.models import Fingerprint
from app.database import get_db
import logging
from enum import Enum
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

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
        #mplementation, obtain from  scanner
        return ScannerCharacteristics(
            dpi=500,
            scan_area=(400, 400),
            image_quality=85,
            noise_level=0.15
        )

    def calculate_dynamic_threshold(self, current_match_score: float) -> int:
        """
        Calculate the dynamic threshold based on security requirements,
        false acceptance/rejection rates, and scanner characteristics.
        """
        # Update historical data
        self.historical_data['match_scores'].append(current_match_score)
        
        # Basic threshold from security level
        base_threshold = self.security_level.value.min_matching_points
        
        # Scanner quality factor (0.8 to 1.2)
        scanner_quality = self._calculate_scanner_quality()
        
        # Performance factor based on historical FAR/FRR (0.9 to 1.1)
        performance_factor = self._calculate_performance_factor()
        
        # Environmental factor (0.95 to 1.05)
        environmental_factor = self._calculate_environmental_factor()
        
        # Calculate final threshold
        dynamic_threshold = math.ceil(
            base_threshold * 
            scanner_quality * 
            performance_factor * 
            environmental_factor *
            self.security_level.value.threshold_multiplier
        )
        
        # Log threshold calculation
        logging.info(f"""
            Threshold Calculation:
            Base: {base_threshold}
            Scanner Quality: {scanner_quality:.2f}
            Performance Factor: {performance_factor:.2f}
            Environmental Factor: {environmental_factor:.2f}
            Final Threshold: {dynamic_threshold}
        """)
        
        return dynamic_threshold

    def _calculate_scanner_quality(self) -> float:
        """Calculate quality factor based on scanner characteristics."""
        # Normalize DPI factor (500 DPI is standard)
        dpi_factor = self.scanner_characteristics.dpi / 500
        
        # Normalize image quality (0-100 scale)
        quality_factor = self.scanner_characteristics.image_quality / 100
        
        # Inverse noise factor (lower noise is better)
        noise_factor = 1 - self.scanner_characteristics.noise_level
        
        # Combine factors with weights
        scanner_quality = (
            0.4 * dpi_factor +
            0.4 * quality_factor +
            0.2 * noise_factor
        )
        
        # Normalize to 0.8-1.2 range
        return 0.8 + (scanner_quality * 0.4)

    def _calculate_performance_factor(self) -> float:
        """Calculate performance factor based on historical FAR/FRR."""
        if not self.historical_data['match_scores']:
            return 1.0

        # Calculate current FAR and FRR from historical data
        current_far = len([x for x in self.historical_data['false_accepts']
                          if x > 0]) / max(len(self.historical_data['false_accepts']), 1)
        current_frr = len([x for x in self.historical_data['false_rejects']
                          if x > 0]) / max(len(self.historical_data['false_rejects']), 1)

        # Compare with target rates
        far_ratio = current_far / self.security_level.value.max_false_accept_rate
        frr_ratio = current_frr / self.security_level.value.max_false_reject_rate

        # Adjust factor based on which rate needs more correction
        if far_ratio > frr_ratio:
            # Increase threshold to reduce FAR
            performance_factor = 1.0 + min(far_ratio - 1, 0.1)
        else:
            # Decrease threshold to reduce FRR
            performance_factor = 1.0 - min(frr_ratio - 1, 0.1)

        return max(0.9, min(1.1, performance_factor))

    def _calculate_environmental_factor(self) -> float:
        """Calculate environmental factor based on current conditions."""
        # In a real implementation, these would be obtained from sensors
        temperature = 22  # Celsius
        humidity = 50    # Percent
        
        # Optimal conditions: 20-25°C, 45-55% humidity
        temp_factor = 1.0 - abs(temperature - 22.5) / 50
        humidity_factor = 1.0 - abs(humidity - 50) / 100
        
        # Combine factors
        environmental_factor = (temp_factor + humidity_factor) / 2
        
        # Normalize to 0.95-1.05 range
        return 0.95 + (environmental_factor * 0.1)

    def update_historical_data(self, match_result: bool, expected_result: bool,
                             match_score: float) -> None:
        """Update historical data with new matching results."""
        if match_result != expected_result:
            if match_result and not expected_result:
                self.historical_data['false_accepts'].append(match_score)
            else:
                self.historical_data['false_rejects'].append(match_score)

        # Keep only recent history (last 1000 matches)
        max_history = 1000
        for key in self.historical_data:
            if len(self.historical_data[key]) > max_history:
                self.historical_data[key] = self.historical_data[key][-max_history:]

class FingerprintService:
    def __init__(self, db: Session = Depends(get_db)):
        self.logger = logging.getLogger(__name__)
        try:
            self.scanner: FingerprintScanner = get_fingerprint_scanner("digitalpersona")
            self.scanner.initialize()
            self.threshold_calculator = ThresholdCalculator(SecurityRequirement.MEDIUM)
        except Exception as e:
            self.logger.error(f"Failed to initialize fingerprint scanner: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Fingerprint scanner initialization failed"
            )
        self.db = db

    # ... (previous methods remain the same)

    def _get_matching_threshold(self) -> int:
        """
        Get the dynamic threshold for fingerprint matching based on current conditions
        and historical performance.
        
        Returns:
            int: The calculated matching threshold
        """
        try:
            # Get the most recent match score (if available)
            recent_scores = self.threshold_calculator.historical_data['match_scores']
            current_score = recent_scores[-1] if recent_scores else 0.5
            
            # Calculate dynamic threshold
            threshold = self.threshold_calculator.calculate_dynamic_threshold(current_score)
            
            self.logger.info(f"Dynamic threshold calculated: {threshold}")
            return threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic threshold: {str(e)}")
            # Fallback to security level's minimum threshold
            return SecurityRequirement.MEDIUM.value.min_matching_points