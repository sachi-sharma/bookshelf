#!/usr/bin/env python
"""
Debug script to run uvicorn with proper path setup
This ensures the app module can be found when running from VS Code debugger
"""
import sys
import os

# Get the backend directory (where this script is located)
backend_dir = os.path.dirname(os.path.abspath(__file__))

# Add backend directory to Python path if not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Print for debugging
print(f"Python path: {sys.path}")
print(f"Backend dir: {backend_dir}")
print(f"Working directory: {os.getcwd()}")

# Try to import app to verify it works
try:
    import app
    print(f"✓ Successfully imported app module")
    if hasattr(app, '__file__'):
        print(f"  Location: {app.__file__}")
except ImportError as e:
    print(f"✗ Failed to import app module: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Files in backend_dir: {os.listdir(backend_dir)}")
    sys.exit(1)

# Now import and run uvicorn
if __name__ == "__main__":
    import uvicorn
    print("Starting uvicorn server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

