from typing import List
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.utils.fingerprint import get_fingerprint_scanner, FingerprintScanner
from app.models import Fingerprint
from app.database import get_db

class FingerprintService:
    def __init__(self, db: Session = Depends(get_db)):
        self.scanner: FingerprintScanner = get_fingerprint_scanner("libfprint")
        self.scanner.initialize()  # Initialize the scanner
        self.db = db

    def capture_fingerprint(self) -> str:
        """Capture a fingerprint using the libfprint scanner."""
        try:
            return self.scanner.capture_fingerprint()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to capture fingerprint: {str(e)}")

    def verify_fingerprint(self, fingerprint_template: str, user_id: int) -> dict:
        """Verify the fingerprint template against stored records."""
        stored_fingerprint = self._get_stored_fingerprint(user_id)
        
        if self._compare_fingerprints(fingerprint_template, stored_fingerprint.fingerprint_template):
            return {"message": "Fingerprint verified successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=400, detail="Fingerprint verification failed")

    def _get_stored_fingerprint(self, user_id: int) -> Fingerprint:
        """Retrieve stored fingerprint for a user."""
        stored_fingerprint = self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first()
        if not stored_fingerprint:
            raise HTTPException(status_code=404, detail="User fingerprint not found")
        return stored_fingerprint

    def _compare_fingerprints(self, new_fingerprint: str, stored_fingerprint: str) -> bool:
        """
        Compare the new fingerprint with the stored fingerprint.
        This uses a simple minutiae-based matching logic for demonstration.
        """
        new_features = self._extract_minutiae(new_fingerprint)
        stored_features = self._extract_minutiae(stored_fingerprint)

        matching_points = sum(1 for feature in new_features if feature in stored_features)
        return matching_points >= self._get_matching_threshold()

    def _extract_minutiae(self, fingerprint: str) -> List[str]:
        """
        Simulated extraction of minutiae features from a fingerprint.
        In reality, this would involve complex image processing and analysis.
        """
        # TODO: Implement actual minutiae extraction
        return fingerprint.split()  # Placeholder implementation

    def _get_matching_threshold(self) -> int:
        """
        Get the threshold for the number of matching points required for verification.
        This could be configurable or dynamically determined based on various factors.
        """
        # TODO: Implement logic to determine the appropriate threshold
        return 3  # Placeholder value

    def register_fingerprint(self, user_id: int) -> dict:
        """Register a new fingerprint for a user."""
        if self._user_has_fingerprint(user_id):
            raise HTTPException(status_code=400, detail="User already has a registered fingerprint")

        fingerprint_template = self.capture_fingerprint()
        new_fingerprint = Fingerprint(user_id=user_id, fingerprint_template=fingerprint_template)
        self.db.add(new_fingerprint)
        self.db.commit()

        return {"message": "Fingerprint registered successfully", "user_id": user_id}

    def _user_has_fingerprint(self, user_id: int) -> bool:
        """Check if a user already has a registered fingerprint."""
        return self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first() is not None
