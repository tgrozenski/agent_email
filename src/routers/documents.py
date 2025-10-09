from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests

# Import shared dependencies from the new dependencies module
from ..dependencies import db_manager, WEB_CLIENT_ID

router = APIRouter()

@router.get("/getDocuments")
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

        documents = db_manager.get_documents(user_email=user_email, content=True, offset=offset, limit=limit)

        return JSONResponse(content={"documents": documents}, status_code=200)
    except Exception as e:
        print("Error getting documents: ", e)
        return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

@router.post("/saveDocument")
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

        success = db_manager.insert_document(
            user_email=user_email,
            doc_name=doc_name,
            text_content=text_content,
            doc_id=doc_id
        )

        if success:
            return JSONResponse(content={"success": f"Content Saved"}, status_code=200)
    except Exception as e:
        if isinstance(e, ValueError):
            return JSONResponse(content={"Error": f"Document is Too Long, error: {e}"}, status_code=400)
        else:
            return JSONResponse(content={"Error": f"Internal Server Error {e}"}, status_code=500)

    return JSONResponse(content={"Error": f"Internal Server Error"}, status_code=500)

@router.get("/getDocumentById")
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

@router.delete("/deleteDocument")
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
