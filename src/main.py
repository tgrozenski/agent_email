from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents, core
import os
import uvicorn

# Create the FastAPI app
app = FastAPI()

# Allows requests from given origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tgrozenski.github.io", "http://localhost:6969"],
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# Include the routers
app.include_router(documents.router)
app.include_router(core.router)

@app.get("/")
def read_root():
    db_manager = db_manager()
    data = db_manager.get_attribute('tyler.grozenski@gmail.com', 'history_id')
    return {"message": f"Server is running.{data}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

