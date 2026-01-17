import os
import base64
import json

def load_service_account():
    b64 = os.environ["LINEWORKS_PRIVATE_KEY_B64"]
    decoded = base64.b64decode(b64)
    return json.loads(decoded)

if __name__ == "__main__":
    print(load_service_account().keys())
