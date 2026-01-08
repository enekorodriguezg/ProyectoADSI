import os

BASE_DIR=os.path.dirname(os.path.abspath(__file__))

class Config:
    DB_PATH=os.path.join(BASE_DIR,"identifier.sqlite")
    SECRET_KEY=os.urandom(24)