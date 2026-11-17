import os
import sys

# Ensure root directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as application

# Both 'app' and 'handler' export for Vercel WSGI
app = application
handler = application
