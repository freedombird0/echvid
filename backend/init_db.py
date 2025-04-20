from flask import Flask
from database import init_db

app = Flask(__name__)

with app.app_context():
    init_db()
    print("✅ Database initialized successfully.")
