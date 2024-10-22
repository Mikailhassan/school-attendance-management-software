import uvicorn
from fastapi import FastAPI
from app import create_app  # Ensure create_app is imported

# Create the FastAPI app using the create_app function
app = create_app()

# Add an endpoint to list all routes (endpoints)
@app.get("/list-endpoints")
def list_endpoints():
    endpoints = []
    for route in app.router.routes:
        endpoints.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods)
        })
    return {"endpoints": endpoints}

if __name__ == "__main__":
    # Running the FastAPI app with uvicorn, and ensuring the import path is correct for reload
    uvicorn.run("app.run:app", host="0.0.0.0", port=8000, reload=True)
