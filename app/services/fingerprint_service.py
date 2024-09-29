# services/fingerprint_service.py

from app.utils.fingerprint import get_fingerprint_scanner
from app.models import Fingerprint, User
from app.database import SessionLocal
from fastapi import HTTPException

class FingerprintService:
    def __init__(self, scanner_type: str):
        self.scanner = get_fingerprint_scanner(scanner_type)
        self.scanner.initialize()
        self.db = SessionLocal()  # Initialize database session

    def capture_fingerprint(self):
        """Capture a fingerprint using the selected scanner."""
        fingerprint_template = self.scanner.capture_fingerprint()
        return fingerprint_template

    def verify_fingerprint(self, fingerprint_template: str, user_id: int):
        """Verify the fingerprint template against stored records."""
        stored_fingerprint = self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first()

        if not stored_fingerprint:
            raise HTTPException(status_code=404, detail="User fingerprint not found")

        # Use a robust comparison method
        is_match = self.compare_fingerprints(fingerprint_template, stored_fingerprint.fingerprint_template)

        if is_match:
            return {"message": "Fingerprint verified successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=400, detail="Fingerprint verification failed")

    def compare_fingerprints(self, new_fingerprint: str, stored_fingerprint: str) -> bool:
        """
        Compare the new fingerprint with the stored fingerprint.
        This uses a simple minutiae-based matching logic for demonstration.
        """
        # Extract features from the fingerprint templates
        new_features = self.extract_minutiae(new_fingerprint)
        stored_features = self.extract_minutiae(stored_fingerprint)

        # Compare the extracted features
        matching_points = sum(1 for feature in new_features if feature in stored_features)

        # Define a threshold for how many points must match
        return matching_points >= 3  # Adjust threshold based on requirements

    def extract_minutiae(self, fingerprint: str):
        """
        Simulated extraction of minutiae features from a fingerprint.
        In reality, this would involve complex image processing and analysis.
        Here we simulate it by returning a list of 'features'.
        """
        # Placeholder: In a real scenario, you'd implement image processing to find minutiae
        return fingerprint.split()  # Splitting by space as a naive feature extractor
