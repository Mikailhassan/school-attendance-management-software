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
        """
        Capture a fingerprint using the selected scanner.
        Returns the fingerprint template.
        """
        fingerprint_template = self.scanner.capture_fingerprint()
        return fingerprint_template

    def verify_fingerprint(self, fingerprint_template: str, user_id: int):
        """
        Verify the fingerprint template against stored records.
        Returns True if the fingerprint matches; otherwise, raises an exception.
        """
        # Fetch the stored fingerprint for the user
        stored_fingerprint = self.db.query(Fingerprint).filter(Fingerprint.user_id == user_id).first()

        if not stored_fingerprint:
            raise HTTPException(status_code=404, detail="User fingerprint not found")

        # Implement verification logic
        is_match = self.compare_fingerprints(fingerprint_template, stored_fingerprint.fingerprint_template)

        if is_match:
            return {"message": "Fingerprint verified successfully"}
        else:
            raise HTTPException(status_code=400, detail="Fingerprint verification failed")

    def compare_fingerprints(self, new_fingerprint: str, stored_fingerprint: str) -> bool:
        """
        Compare the new fingerprint with the stored fingerprint.
        This method should implement the actual comparison logic.
        For this example, we'll perform a simple equality check.
        """
        return new_fingerprint == stored_fingerprint 
