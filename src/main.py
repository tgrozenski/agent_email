import os
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Gemini client with the API key from environment variables
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])

# Create the FastAPI app
app = FastAPI()

origins = [
    "https://tgrozenski.github.io",
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)


def get_text_content(prompt: str) -> str:
    """Generates text content using the Gemini model."""
    logger.info(f"Generating content for prompt: {prompt[:30]}...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        logger.info("Successfully generated content from Gemini.")
        return response.text
    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        raise

@app.post("/webhook")
async def webhook(request: Request):
    """
    This endpoint receives a POST request with a JSON payload,
    sends the "prompt" from the payload to the Gemini API,
    and returns the Gemini API's response.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt")

        if not prompt:
            logger.warning("Prompt not found in request body")
            return JSONResponse(content={"error": "Prompt not found in request body"}, status_code=400)

        # Send the prompt to the Gemini API
        response = get_text_content(prompt)

        # Return the Gemini API's response
        logger.info("Webhook processed successfully.")
        return JSONResponse(content={"response": response})

    except Exception as e:
        logger.error(f"An error occurred in the webhook: {e}")
        return JSONResponse(content={"error": "An internal server error occurred."}, status_code=500)

"""
This is the endpoint to exchange the permission code with token to be used by our API
Note: requires running frontend and backend simultaneously on localhost
"""
@app.post("/register")
async def recieve_auth_code(request: Request):
    # Gets token
    flow: Flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=['email']
    )

    auth_code = await request.json()
    print("this is the auth code", auth_code)
    token: dict = flow.fetch_token(code=auth_code['code'])

    # try:
    #     idinfo = id_token.verify_oauth2_token(token, requests.Request(), WEB_CLIENT_ID)
    #     print(idinfo)
    # except Exception as e:
    #     print(e)
    #     print('request didnt go through')

    # Create user profile using information from the token
    # Creates new user and inserts into the database
    ...

# This method endpoint will be 'subscribed' to the pub/sub endpoint
@app.post("/processEmail")
def pub_sub(request: Request):
    ...

@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}
