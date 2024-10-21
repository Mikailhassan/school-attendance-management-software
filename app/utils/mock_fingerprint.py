# Create a new file: app/utils/mock_fingerprint.py

import numpy as np
from typing import Dict, Any
import asyncio
from datetime import datetime

class MockFingerprint:
    def __init__(self):
        self.quality_threshold = 0.7  # Higher threshold for mock data
        self.mock_users = {
            "teacher_1": {"id": "T001", "role": "teacher"},
            "teacher_2": {"id": "T002", "role": "teacher"},
            "student_1": {"id": "S001", "role": "student"},
            # Add more mock users as needed
        }

    async def generate_mock_fingerprint_data(self) -> Dict[str, Any]:
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Randomly select a mock user
        user = np.random.choice(list(self.mock_users.values()))
        
        # Generate a mock template
        template = {
            "user_id": user["id"],
            "role": user["role"],
            "timestamp": datetime.now().isoformat(),
            "quality_score": 0.8,  # High quality score for testing
            "template_data": np.random.bytes(512)  # Mock biometric template
        }
        
        return {
            "raw_image": np.random.randint(0, 256, (500, 500), dtype=np.uint8),
            "enhanced_image": np.random.randint(0, 256, (500, 500), dtype=np.uint8),
            "segmented_image": np.random.randint(0, 256, (500, 500), dtype=np.uint8),
            "quality_score": 0.8,
            "template": template,
        }