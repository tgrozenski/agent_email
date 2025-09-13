import os
from db_manager import DBManager
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google.auth.transport import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from CredentialsManager import CredentialsManager

WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]

# Configure the Gemini client with the API key from environment variables
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])
db_manager = DBManager()

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
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


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
            return JSONResponse(content={"error": "Prompt not found in request body"}, status_code=400)

        # Send the prompt to the Gemini API
        response = get_text_content(prompt)

        # Return the Gemini API's response
        return JSONResponse(content={"response": response})

    except Exception as e:
        return JSONResponse(content={"error": f"An internal server error occurred. error: {e}"}, status_code=500)


"""
This is the endpoint to exchange the permission code with token to be used by our API
Note: requires running frontend and backend simultaneously on localhost
"""
@app.post("/register")
async def recieve_auth_code(request: Request):

    # get token
    token = await CredentialsManager.get_initial_token(request)

    try:
        idinfo = id_token.verify_oauth2_token(
            token['id_token'], requests.Request(), WEB_CLIENT_ID
        )
        
        user_name = idinfo.get('name', 'N\A')
        user_email = idinfo.get('email')
        refresh_token = token.get('refresh_token')

        creds = Credentials(token=token['access_token'])
        CredentialsManager.creds = creds

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        initial_history_id = profile.get('historyId')

        # insert new credentials into db
        db_manager.insert_new_user(
            name=user_name,
            user_email=user_email,
            refresh_token=refresh_token,
            historyID=initial_history_id
        )

    except Exception as e:
        print(f"Token verification failed: {e}")
        return JSONResponse(content={"error": f"Token verification failed. {e}"}, status_code=400)

    return {"message": f"User {user_email} successfully registered.", "id_token": token['id_token']}

@app.get("/getDocuments")
async def get_documents(request: Request):
    """
    Recieves a user email from the frontend to get all documents associated with that user
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(content={"error": "Authorization header missing"}, status_code=401)

        try:
            # The token is expected to be in the format "Bearer <token>"
            id_token_value = auth_header.split(" ")[1]
            idinfo = id_token.verify_oauth2_token(
                id_token_value, requests.Request(), WEB_CLIENT_ID
            )
            user_email = idinfo.get('email')
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        user_id = db_manager.get_attribute(
            attribute="user_id",
            user_email=user_email
        )

        documents = db_manager.get_documents(user_id=user_id)

        return JSONResponse(content={"documents": documents}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

@app.post("/saveDocument")
async def save_document(request: Request):
    """
    Recieves a document from the frontend to be saved in the DB for RAG
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(content={"error": "Authorization header missing"}, status_code=401)

        try:
            # The token is expected to be in the format "Bearer <token>"
            id_token_value = auth_header.split(" ")[1]
            idinfo = id_token.verify_oauth2_token(
                id_token_value, requests.Request(), WEB_CLIENT_ID
            )
            user_email = idinfo.get('email')
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        data = await request.json()
        doc_name = data.get("doc_name")
        text_content = data.get("text_content")
        user_id = db_manager.get_attribute(
            attribute="user_id",
            user_email=user_email
        )

        flag = db_manager.insert_document(
            user_id=user_id,
            doc_name=doc_name,
            text_content=text_content
        )

        if flag:
            return JSONResponse(content={"success": f"Content Saved"}, status_code=200)
    except Exception as e:
        if isinstance(e, ValueError):
            return JSONResponse(content={"Error": f"Document is Too Long, error: {e}"}, status_code=400)
        else:
            return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

    return JSONResponse(content={"Error": f"Internal Server Error"}, status_code=500)

"""
An endpoint that is subscribed to the pub/sub topic
Responsible to
    - get short lived access token from refresh token (for gmail api)
    - determine emails since last historyID
    - process those emails
    - query gemini api for response
    - write draft with gmail api
    - update last historyID in DB
"""
@app.post("/processEmail")
async def pub_sub(request: Request):
    ...
    # pub_sub_dict = await request.json()
    
    # # The data from pub/sub is base64 encoded and contains the user's email
    # message_data = base64.b64decode(pub_sub_dict['message']['data']).decode('utf-8')
    # message_json = json.loads(message_data)
    # user_email = message_json['emailAddress']

    # refresh_token = db_manager.get_refresh_token(user_email)
    # access_token = get_access_token(refresh_token)
    # start_history_id = db_manager.get_history_id(user_email)

    # emails: list = get_unprocessed_emails(access_token, start_history_id)

    # if not emails:
    #     return {"message": "No new emails to process."}

    # for email in emails:
    #     response_body = get_response_body(email)
    #     publish_draft(access_token, response_body, email.messageID)
    
    # # Update the history ID to the latest one from the processed batch
    # latest_history_id = max(int(email.historyID) for email in emails)
    # db_manager.update_historyID(user_email, str(latest_history_id))

    # return {"message": f"Successfully processed {len(emails)} emails."}


@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}