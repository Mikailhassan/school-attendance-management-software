import uvicorn
from app import create_app  # Ensure create_app is imported

app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.__init__:create_app", host="0.0.0.0", port=8000, reload=True)