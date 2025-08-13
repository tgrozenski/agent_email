import os
import psycopg2
import pg8000.dbapi
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]

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
        'AgentEmailWebClientSecrets.json',
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
    )

    flow.redirect_uri = 'https://tgrozenski.github.io/agent_email_frontend.github.io/callback.html'

    auth_code = await request.json()
    token: dict = flow.fetch_token(code=auth_code['code'])
    user_name, user_email = None, None

    try:
        idinfo = id_token.verify_oauth2_token(
            token['id_token'], requests.Request(), WEB_CLIENT_ID
        )
        
        # Extract user info
        user_name = idinfo.get('name', 'N/A')
        user_email = idinfo.get('email', 'N/A')

        user_info_string = f"User: {user_name}, Email: {user_email}"
        print(user_info_string)

    except Exception as e:
        print(f"Token verification failed: {e}")

    # Connect to postgresSQL and insert new user
    if user_name and user_email:
        try:
            conn = pg8000.dbapi.connect(
                user="avnadmin",
                password=AIVEN_PASSWORD,
                host="pg-38474cd-agent-email.e.aivencloud.com",
                port=17757,
                database="defaultdb"
            )
            cur = conn.cursor()
            cur.execute('INSERT INTO "user" (name, email) VALUES (%s, %s)', (user_name, user_email))
            conn.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            conn.close()

    return {"message": f"User with email {user_email} and name {user_name} has been saved"}

# This method endpoint will be 'subscribed' to the pub/sub endpoint
@app.post("/processEmail")
def pub_sub(request: Request):
    ...

@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}
