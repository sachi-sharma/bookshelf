# Debugging Guide

This guide explains how to debug the Smart Bookshelf application.

## Prerequisites

### VS Code Extensions

Install these extensions in VS Code/Cursor:

1. **Python** (`ms-python.python`) - For backend debugging
2. **Python Debugger** (`ms-python.debugpy`) - Python debugger
3. **Debugger for Chrome** (`msjsdiag.debugger-for-chrome`) - For frontend debugging (optional, Chrome DevTools also works)

## Backend Debugging (FastAPI)

### Option 1: Using VS Code Debug Configuration
 
1. **Open the Debug Panel**: Press `Cmd+Shift+D` (Mac) or `Ctrl+Shift+D` (Windows/Linux)
2. **Select Configuration**: Choose "Python: FastAPI Backend" from the dropdown
3. **Set Breakpoints**: Click in the gutter next to line numbers in Python files
4. **Start Debugging**: Press `F5` or click the green play button

The backend will start on `http://localhost:8000` with debugging enabled.

### Option 2: Manual Debugging

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run with Python debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

Then attach the VS Code debugger to port 5678.

### Option 3: Using Python's Built-in Debugger (pdb)

Add breakpoints in your code:

```python
import pdb; pdb.set_trace()
```

Or use `breakpoint()` (Python 3.7+):

```python
def some_function():
    breakpoint()  # Execution will pause here
    # Your code
```

### Debugging Tips

- **Set breakpoints** in API endpoints, services, or models
- **Inspect variables** in the Debug sidebar
- **Use Debug Console** to evaluate expressions
- **Step through code** with F10 (step over), F11 (step into), Shift+F11 (step out)

## Frontend Debugging (React)

### Option 1: Using VS Code Debug Configuration

1. **Start the dev server** (if not already running):
   ```bash
   cd frontend
   npm run dev
   ```

2. **Open Debug Panel**: Press `Cmd+Shift+D`
3. **Select Configuration**: Choose "React: Frontend (Chrome)" or "React: Frontend (Edge)"
4. **Set Breakpoints**: In TypeScript/TSX files
5. **Start Debugging**: Press `F5`

This will open Chrome/Edge with debugging enabled.

### Option 2: Chrome DevTools

1. **Start the dev server**:
   ```bash
   cd frontend
   npm run dev
   ```

2. **Open Chrome** and navigate to `http://localhost:3000`
3. **Open DevTools**: Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)
4. **Set breakpoints** in the Sources tab
5. **Use Console** for logging and debugging

### Option 3: React Developer Tools

Install the [React Developer Tools](https://react.dev/learn/react-developer-tools) browser extension for component inspection.

### Debugging Tips

- **Use `console.log()`** for quick debugging
- **Set breakpoints** in TypeScript files
- **Inspect React components** with React DevTools
- **Check Network tab** for API calls
- **Use React Query DevTools** (if installed) for data fetching debugging

## Full Stack Debugging

### Debug Both Backend and Frontend Simultaneously

1. **Open Debug Panel**: `Cmd+Shift+D`
2. **Select**: "Full Stack: Backend + Frontend"
3. **Press F5**

This starts both servers and attaches debuggers to both.

## Common Debug Scenarios

### Debugging API Endpoints

1. Set a breakpoint in an API route (e.g., `backend/app/api/books.py`)
2. Start backend debugger
3. Make a request from frontend or Postman
4. Execution will pause at the breakpoint

### Debugging Database Queries

1. Set breakpoint in a service function (e.g., `backend/app/services/book_service.py`)
2. Inspect the `db` session object
3. Check SQLAlchemy query results

### Debugging React Components

1. Set breakpoint in a component (e.g., `frontend/src/pages/Dashboard.tsx`)
2. Start frontend debugger
3. Interact with the UI
4. Execution will pause at the breakpoint

### Debugging API Calls

1. Set breakpoint in API service (e.g., `frontend/src/services/api.ts`)
2. Set breakpoint in corresponding backend endpoint
3. Make a request from frontend
4. Step through both frontend and backend code

## Debugging Configuration Files

- **`.vscode/launch.json`**: Debug configurations
- **`.vscode/tasks.json`**: Background tasks (dev servers)
- **`.vscode/settings.json`**: Workspace settings

## Troubleshooting

### Backend Debugger Not Starting

- Ensure virtual environment is activated
- Check Python interpreter is set correctly
- Verify `debugpy` is installed: `pip install debugpy`

### Frontend Debugger Not Attaching

- Ensure dev server is running on port 3000
- Check browser allows debugging (Chrome: `chrome://inspect`)
- Try using "Attach to Chrome" configuration instead

### Breakpoints Not Hitting

- Ensure source maps are enabled (they are by default in Vite)
- Check file paths match exactly
- Try restarting the debugger
- For Python: Ensure `justMyCode: false` in launch.json

## Quick Reference

| Action | Shortcut (Mac) | Shortcut (Windows/Linux) |
|--------|---------------|-------------------------|
| Start Debugging | `F5` | `F5` |
| Stop Debugging | `Shift+F5` | `Shift+F5` |
| Step Over | `F10` | `F10` |
| Step Into | `F11` | `F11` |
| Step Out | `Shift+F11` | `Shift+F11` |
| Continue | `F5` | `F5` |
| Toggle Breakpoint | `F9` | `F9` |

## Example: Debugging a Reading Session Creation

1. **Set breakpoint** in `backend/app/api/sessions.py` at the `create_reading_session` function
2. **Set breakpoint** in `frontend/src/pages/Dashboard.tsx` where the API call is made
3. **Start full stack debugger**
4. **Trigger the action** from the UI
5. **Step through** both frontend and backend code to see the data flow

This helps you understand:
- What data is sent from frontend
- How it's processed in the backend
- What response is returned
- How the frontend handles the response

