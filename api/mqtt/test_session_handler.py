from session_handler import SessionHandler
import time
import signal
import sys


def signal_handler(sig, frame):
    print("\nShutting down session handler...")
    session_handler.cleanup()
    sys.exit(0)


if __name__ == "__main__":
    # Create session handler
    session_handler = SessionHandler()

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    print("Session handler started. Press Ctrl+C to stop.")
    print("Waiting for Arduino messages...")

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
