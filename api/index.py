import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)

try:
    from app import app
except Exception as e:
    logging.exception("Failed to import app")
    from flask import Flask
    app = Flask(__name__)

    @app.route('/')
    def error_page():
        return f"<h1>Import Error</h1><pre>{e}</pre>", 500
