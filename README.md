# AI-Powered Email Assistant

This project is a backend service that helps users manage their email by leveraging a personal knowledge base. It allows users to store documents and uses that information to help draft intelligent, context-aware replies to incoming emails.

## Core Functionality

The application is built to connect a user's knowledge with their email workflow.

1.  **Document Management**: Users can create, read, update, and delete documents through a secure API. This collection of documents forms a personal knowledge base.
2.  **Email Processing**: When a new email arrives in a user's inbox, the service is notified by Google.
3.  **Contextual Search**: The service analyzes the content of the new email and searches the user's knowledge base to find the most relevant information.
4.  **Automated Draft Generation**: The content of the email and the most relevant documents are sent to a generative AI model, which produces a helpful draft reply. This draft is then saved directly in the user's Gmail account, ready for them to review, edit, and send.

## Technologies Used

- **Backend**: Python with the **FastAPI** framework.
- **Database**: **PostgreSQL** hosted on Aiven, with the **`pgvector`** extension for efficient similarity search.
- **Vector Embeddings**: The **`FastEmbed`** library for generating high-quality text embeddings.
- **Authentication**: Google OAuth 2.0 for secure, user-consented access to the Gmail API.
- **Generative AI**: Google's Gemini API for generating draft email responses.
- **Deployment**: Containerized with **Docker** and deployed on **Google Cloud Run**. Cron jobs are managed by **Google Cloud Scheduler**.

## API Endpoints

All document-related endpoints require a valid `Authorization: Bearer <ID_TOKEN>` header for authentication.

### Authentication

#### `POST /login`
- **Purpose**: Handles the final step of the Google OAuth 2.0 flow to register or log in a user.
- **Process**:
    1. Receives a temporary authorization code from the frontend after the user grants consent.
    2. Securely exchanges this code for a long-lived **refresh token** and an ID token.
    3. Verifies the user's identity.
    4. Stores the user's name, email, and encrypted refresh token in the database.
    5. Sets up the initial Gmail watch to monitor for new emails.
- **Returns**: A success message and the user's `id_token` for use in subsequent API calls.

### Documents

#### `POST /saveDocument`
- **Purpose**: Saves a new document or updates an existing one in the user's knowledge base.
- **Request Body**:
    ```json
    {
        "doc_name": "My Document Title",
        "text_content": "The full text content of the document goes here.",
        "doc_id": "optional-document-id-to-update"
    }
    ```
- **Returns**: A success or error JSON response.

#### `GET /getDocuments`
- **Purpose**: Retrieves a paginated list of a user's documents.
- **Query Parameters**: `limit` (integer, default 20), `offset` (integer, default 0).
- **Returns**: A JSON array of document objects, each containing `id` and `name`.

#### `GET /getDocument/{doc_id}`
- **Purpose**: Retrieves the full content of a single document by its ID.
- **Returns**: A JSON object containing the document's `id`, `name`, and `content`.

#### `DELETE /deleteDocument/{doc_id}`
- **Purpose**: Deletes a document from the user's knowledge base.
- **Returns**: A success or error JSON response.

### Internal Operations

#### `POST /processEmails`
- **Purpose**: The webhook endpoint triggered by Google Pub/Sub when a new email arrives. This endpoint is not intended for direct user interaction.
- **Process**:
    1. Receives a notification containing the user's email address.
    2. Fetches the user's credentials and new emails from the Gmail API.
    3. For each relevant email, it finds related documents from the user's knowledge base.
    4. Uses the Gemini API to generate a draft reply based on the email and document context.
    5. Saves the draft in the user's Gmail account.
    6. Updates the user's email history marker to prevent reprocessing.

#### `POST /tasks/renew-gmail-watch`
- **Purpose**: An internal endpoint designed to be called by a cron job to renew the Gmail watch subscription for all users.
- **Security**: This endpoint is protected and requires a secret token to be passed in the `x-internal-secret` header.
- **Process**: Iterates through all users in the database and sends a request to the Gmail API to extend their watch notification subscription, ensuring the service continues to receive new email alerts.
