from dotenv import load_dotenv
load_dotenv()  # loads .env from cwd or parent directories
import os
from cryptography.fernet import Fernet


def get_encryption_key():
    key_file_path = os.getenv('KEY_FILE_PATH')
    if os.path.exists(key_file_path):
        with open(key_file_path, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file_path, 'wb') as f:
            f.write(key)
        return key

ENCRYPTION_KEY = get_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)

if __name__ == '__main__':
    encrypted_pass = cipher.encrypt(b'apspp')
    print(encrypted_pass)