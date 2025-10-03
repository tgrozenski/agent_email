from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents, core

# Create the FastAPI app
app = FastAPI()

# Allows requests from given origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tgrozenski.github.io"],
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# Include the routers
app.include_router(documents.router)
app.include_router(core.router)

@app.get("/")
def read_root():
    return {"message": "Server is running."}