from jose import jwt
from dotenv import load_dotenv
import os

load_dotenv()

SECRET = os.environ["secret"]
ALGORITHM = os.environ["algorithm"]


def create_token(email: str):
    return jwt.encode(
        {"email": email, "project": "NewsStream"},
        SECRET,
        algorithm=ALGORITHM,
    )


def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])