# This file contains helper functions to perform validation on the data received from the client.

# Used to validate the 'base64_image' field in the request payload
def validate_embedding(embedding):
    # TODO: ask Thomas for clarification on the expected format of the 'facial_embedding' field
        # will it be 128 floats in a list?
    if not isinstance(embedding, list) or len(embedding) != 128:
        return False, "Invalid 'facial_embedding' format. Must be a list of 128 floats."
    if not all(isinstance(x, (float, int)) for x in embedding):
        return False, "'facial_embedding' must contain numeric values."
    return True, ""

# Used to validate the 'rfid_tag' field in the request payload
def validate_rfid(rfid_tag):
    if not isinstance(rfid_tag, str):
        return False, "Invalid 'rfid_tag' format. Must be a string."
    return True, ""
