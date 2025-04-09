from queue import Queue
from dataclasses import dataclass
from enum import Enum

'''
This file contains the dataclasses and enums for the verification request

The VerificationType enum is used to specify the type of verification request
The VerificationRequest dataclass is used to represent a verification request

The use case for this is to allow the endpoint to send a verification request to a queue for processing
The queue will then be consumed by a worker that will process the verification request
'''


class VerificationType(Enum):
    RFID_AND_IMAGE = "rfid_and_image"
    RFID_ONLY = "rfid_only"
    IMAGE_ONLY = "image_only"


@dataclass
class VerificationRequest:
    type: VerificationType
    session_id: str
    rfid_tag: str = None
    image_data: bytes = None
    embedding: list = None
