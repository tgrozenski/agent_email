from db_manager import DBManager
import base64, json, os
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
from mail import *

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


"""
This is the endpoint to exchange the permission code with token to be used by our API
"""
@app.post("/login")
async def recieve_auth_code(request: Request):

    # get token
    token = await CredentialsManager.get_initial_token(request)

    try:
        idinfo = id_token.verify_oauth2_token(
            token['id_token'], requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
        )

        user_name = idinfo.get('name', 'N\A')
        user_email = idinfo.get('email')
        refresh_token = token.get('refresh_token')

        creds = Credentials(token=token['access_token'])
        CredentialsManager.creds = creds

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        initial_history_id = profile.get('historyId')

        # insert new credentials into db, if user already exists nothing will be done
        db_manager.insert_new_user(
            name=user_name,
            user_email=user_email,
            refresh_token=refresh_token,
            historyID=initial_history_id
        )

    except Exception as e:
        print(f"Token verification failed: {e}")
        return JSONResponse(content={"error": f"Token verification failed. {e}"}, status_code=400)

    return JSONResponse(content = {
        "message": f"User {user_email} successfully registered.",
        "id_token": token['id_token']
        }, status_code=200)

@app.get("/getDocuments")
async def get_documents(request: Request, offset: int = 0, limit: int = 10):
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
                id_token_value, requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
            )
            user_email = idinfo.get('email')
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        user_id = db_manager.get_attribute(
            attribute="user_id",
            user_email=user_email
        )
        documents = db_manager.get_documents(user_id=user_id, content=True, offset=offset, limit=limit)

        return JSONResponse(content={"documents": documents}, status_code=200)
    except Exception as e:
        print("Error getting documents: ", e)
        return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

@app.post("/saveDocument")
async def save_document(request: Request):
    """
    Recieves a document from the frontend to be saved in the DB for RAG
    Note: passing a doc_id will update an existing document instead of creating a new one
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(content={"error": "Authorization header missing"}, status_code=401)

        try:
            # The token is expected to be in the format "Bearer <token>"
            id_token_value = auth_header.split(" ")[1]
            idinfo = id_token.verify_oauth2_token(
                id_token_value, requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
            )
            user_email = idinfo.get('email')
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        data = await request.json()
        doc_name = data.get("doc_name")
        text_content = data.get("text_content")
        doc_id = data.get("doc_id", None) # optional, for updating existing document

        user_id = db_manager.get_attribute(
            attribute="user_id",
            user_email=user_email
        )

        flag = db_manager.insert_document(
            user_id=user_id,
            doc_name=doc_name,
            text_content=text_content,
            doc_id=doc_id
        )

        if flag:
            return JSONResponse(content={"success": f"Content Saved"}, status_code=200)
    except Exception as e:
        if isinstance(e, ValueError):
            return JSONResponse(content={"Error": f"Document is Too Long, error: {e}"}, status_code=400)
        else:
            return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

    return JSONResponse(content={"Error": f"Internal Server Error"}, status_code=500)

@app.get("/getDocumentById")
async def get_document_by_id(request: Request, doc_id: str):
    """
    Recieves a document ID from the frontend to get the document content associated with that ID
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(content={"error": "Authorization header missing"}, status_code=401)

        try:
            # The token is expected to be in the format "Bearer <token>"
            id_token_value = auth_header.split(" ")[1]
            id_token.verify_oauth2_token( # ensuring token is valid
                id_token_value, requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
            )
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        document = db_manager.get_document_by_id(doc_id=doc_id)
        if document is None:
            return JSONResponse(content={"error": "Document not found or access denied"}, status_code=404)

        return JSONResponse(content={"document": document}, status_code=200)
    except Exception as e:
        print("Error getting document by ID: ", e)
        return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)
    
@app.delete("/deleteDocument")
async def delete_document(request: Request, doc_id: str):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JSONResponse(content={"error": "Authorization header missing"}, status_code=401)

        try:
            id_token_value = auth_header.split(" ")[1]
            id_token.verify_oauth2_token( # just verifying token is valid
                id_token_value, requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
            )
        except Exception as e:
            return JSONResponse(content={"error": f"Invalid token: {e}"}, status_code=401)

        success = db_manager.delete_document(doc_id)
        print("success: ", success, "deleting doc id", doc_id)
        if not success:
            return JSONResponse(content={"error": "Document not found or could not be deleted"}, status_code=404)

        return JSONResponse(content={"Success": "Document was deleted"}, status_code=200)

    except Exception as e:
        print("Error getting document by ID: ", e)
        return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)


"""
An endpoint that is subscribed to the pub/sub topic
Recieves a pub sub message from google indicating a change in the user's mailbox
Must:
    - get short lived access token from refresh token (for gmail api)
    - determine emails since last historyID
    - process those emails
    - query gemini api for response
    - write draft with gmail api
    - update last historyID in DB
"""
@app.post("/processEmails")
async def pub_sub(request: Request):
    pub_sub_dict = await request.json()

    # The data from pub/sub is base64 encoded and contains the user's email
    message_data = base64.b64decode(pub_sub_dict['message']['data']).decode('utf-8')
    message_json = json.loads(message_data)
    user_email = message_json['emailAddress']

    # get refresh token and historyID from db
    refresh_token = db_manager.get_attribute(user_email, "encrypted_refresh_token")
    print("LOG\n\n\ngot encrypted refresh token: ", refresh_token)
    print("LOG\n\n\ngot user_email: ", user_email)

    start_history_id = db_manager.get_attribute(user_email, "history_id")

    # use gmail api to get emails since last historyID
    creds_manager: CredentialsManager = CredentialsManager(refresh_token=refresh_token)
    emails: list[Email] = get_unprocessed_emails(creds_manager.creds, start_history_id)
    
    print("LOG \n\n\n")
    print("These are all the last emails fetched")
    print([type(email) for email in emails])

    if not emails:
        print("LOG: No new emails to process.")

    for email in emails:
        if not email.body or is_likely_unimportant(email):
            continue

        user_id = db_manager.get_attribute(user_email, "user_id"),
        print("This is user id:", user_id)
        response_body = get_ai_draft(
            user_id,
            email,
            client,
            db_manager
        )

        publish_draft(creds_manager.creds, response_body, email.messageID)

    # Update the history ID to the latest one from the processed batch
    if emails:
        latest_history_id = max(int(email.historyID) for email in emails)
        db_manager.update_historyID(user_email, str(latest_history_id))
    print(f"Successfully processed {len(emails)} emails.")

    # As per google documentation we must return a 200 ack
    return JSONResponse(content={}, status_code=200)


@app.get("/")
def read_root():
    return {"message": "Server is running."}
