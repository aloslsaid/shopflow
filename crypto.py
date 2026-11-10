import os
from cryptography.fernet import Fernet
def _f(): return Fernet(os.environ["CREDENTIALS_KEY"].encode())
def encrypt(s: str) -> str: return _f().encrypt(s.encode()).decode()
def decrypt(s: str) -> str: return _f().decrypt(s.encode()).decode()
