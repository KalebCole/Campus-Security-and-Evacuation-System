from rfid_handler import RFIDHandler
import time
import signal
import sys


def signal_handler(sig, frame):
    print("\nShutting down RFID handler...")
    rfid_handler.cleanup()
    sys.exit(0)


if __name__ == "__main__":
    # Create RFID handler
    rfid_handler = RFIDHandler()

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    print("RFID handler started. Press Ctrl+C to stop.")
    print("Waiting for RFID scans...")

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
