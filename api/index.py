"""Vercel serverless giris noktasi."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('INSTANCE_PATH', '/tmp/instance')
os.environ.setdefault('UPLOAD_FOLDER', '/tmp/uploads')

from app import create_app

app = create_app()
