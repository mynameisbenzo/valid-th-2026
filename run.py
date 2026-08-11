"""Simple launcher: `python run.py` starts the API on http://127.0.0.1:8000

This does the same thing as `uvicorn valid_video.api:app --reload`, just
as a single script in case that's a more familiar way to start things.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("valid_video.api:app", host="127.0.0.1", port=8000, reload=True)
