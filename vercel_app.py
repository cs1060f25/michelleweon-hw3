# Vercel-compatible Flask app entry point
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import app

# This is the entry point for Vercel
def handler(request):
    return app(request.environ, lambda *args: None)
