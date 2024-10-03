import serial
import time
from abc import ABC, abstractmethod

class FingerprintScanner(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize the fingerprint scanner."""
        pass

    @abstractmethod
    def capture_fingerprint(self):
        """Capture a fingerprint and return the template."""
        pass

class SerialFingerprintScanner(FingerprintScanner):
    def __init__(self, port: str, baudrate: int = 57600, timeout: int = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def initialize(self):
        try:
            self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
            print("Serial fingerprint scanner initialized.")
        except serial.SerialException as e:
            raise RuntimeError(f"Error initializing serial scanner: {e}")

    def capture_fingerprint(self):
        if not self.ser:
            raise RuntimeError("Scanner not initialized. Call initialize() first.")

        print("Waiting for fingerprint scan...")
        time.sleep(2)  # Simulate the time taken for the fingerprint scan
        
        try:
            self.ser.write(b'CAPTURE')  
            fingerprint_template = self.ser.readline().decode('utf-8').strip()
            print(f"Captured fingerprint data: {fingerprint_template}")
            return fingerprint_template
        except serial.SerialException as e:
            raise RuntimeError(f"Error capturing fingerprint: {e}")

class NetworkFingerprintScanner(FingerprintScanner):
    def __init__(self, api_url: str):
        self.api_url = api_url

    def initialize(self):
        print(f"Network fingerprint scanner initialized with API URL: {self.api_url}")

    def capture_fingerprint(self):
        print("Capturing fingerprint using network scanner...")
        
        # TODO: Implement actual network API call
        fingerprint_template = "network_fingerprint_template_data"
        print(f"Captured fingerprint data: {fingerprint_template}")
        return fingerprint_template

def get_fingerprint_scanner(scanner_type: str, **kwargs) -> FingerprintScanner:
    """Factory function to get the appropriate fingerprint scanner."""
    scanners = {
        "serial": SerialFingerprintScanner,
        "network": NetworkFingerprintScanner
    }
    
    scanner_class = scanners.get(scanner_type)
    if not scanner_class:
        raise ValueError(f"Unsupported scanner type: {scanner_type}")
    
    return scanner_class(**kwargs)