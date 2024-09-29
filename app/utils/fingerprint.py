# app/utils/fingerprint.py

import serial
import time

class FingerprintScanner:
    def initialize(self):
        """Initialize the fingerprint scanner."""
        raise NotImplementedError("Subclasses should implement this method.")

    def capture_fingerprint(self):
        """Capture a fingerprint and return the template."""
        raise NotImplementedError("Subclasses should implement this method.")

class SerialFingerprintScanner(FingerprintScanner):
    def __init__(self, port: str):
        self.port = port
        self.ser = None

    def initialize(self):
        """Initialize the serial fingerprint scanner."""
        try:
            self.ser = serial.Serial(self.port, baudrate=57600, timeout=1)
            print("Serial fingerprint scanner initialized.")
        except Exception as e:
            raise RuntimeError(f"Error initializing serial scanner: {e}")

    def capture_fingerprint(self):
        """Capture fingerprint data via the serial connection."""
        if not self.ser:
            raise RuntimeError("Scanner not initialized. Call initialize() first.")

        print("Waiting for fingerprint scan...")
        time.sleep(2)  # Simulate the time taken for the fingerprint scan
        
        # Send command to capture fingerprint
        self.ser.write(b'CAPTURE')  # Replace with the actual command
        fingerprint_template = self.ser.readline().decode('utf-8').strip()  # Read response from scanner
        
        print(f"Captured fingerprint data: {fingerprint_template}")
        return fingerprint_template

class NetworkFingerprintScanner(FingerprintScanner):
    def initialize(self):
        """Initialize the network fingerprint scanner."""
        print("Network fingerprint scanner initialized.")

    def capture_fingerprint(self):
        """Capture fingerprint data via network API."""
        print("Capturing fingerprint using network scanner...")
        
        # Simulated network fingerprint capture; replace with actual implementation
        fingerprint_template = "network_fingerprint_template_data"
        print(f"Captured fingerprint data: {fingerprint_template}")
        return fingerprint_template

def get_fingerprint_scanner(scanner_type: str) -> FingerprintScanner:
    """Factory function to get the appropriate fingerprint scanner."""
    if scanner_type == "serial":
        return SerialFingerprintScanner(port='/dev/ttyUSB0')  # Specify your port
    elif scanner_type == "network":
        return NetworkFingerprintScanner()
    else:
        raise ValueError(f"Unsupported scanner type: {scanner_type}")
