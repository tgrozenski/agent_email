# Agent Email: Semantic Knowledge Base

This project is a Python-based backend service that provides a personal knowledge base for users. It allows users to store documents and then search through them based on conceptual meaning rather than just keywords.

The core of this application is a Retrieval-Augmented Generation (RAG) system that uses vector embeddings to find the most relevant documents for a user's query, which can then be used to assist in tasks like drafting intelligent email responses.

## Core Methodology: Retrieval-Augmented Generation (RAG)

This application leverages the power of vector search to create a semantic knowledge base. The process is as follows:

1.  **Document Ingestion & Embedding**: When a user saves a document, the text content and its title are combined. A machine learning model then converts this text into a 384-dimension numerical vector (an "embedding"). This vector represents the document's semantic meaning.
2.  **Storage**: The original text and its corresponding vector embedding are stored in a PostgreSQL database, linked to the user's ID.
3.  **Semantic Search**: When a user submits a search query, that query is also converted into a 384-dimension vector.
4.  **Similarity Search**: The system uses a **cosine similarity** search to compare the query's vector against all the document vectors for that user. The database then returns the "top-k" most similar documents—those whose meaning is closest to the user's query.

## Technologies Used

- **Backend**: Python with the **FastAPI** framework for creating a fast, modern API.
- **Database**: **PostgreSQL** hosted on Aiven.
- **Vector Search**: The **`pgvector`** extension for PostgreSQL, which enables storing and searching vector embeddings efficiently.
- **Vector Embeddings**: The **`FastEmbed`** library, a lightweight and CPU-optimized library for generating high-quality text embeddings using the `BAAI/bge-small-en-v1.5` model (384 dimensions).
- **Database Driver**: `pg8000` for connecting the Python application to the PostgreSQL database.
- **Authentication**: Google OAuth 2.0 for secure, user-consented access to Gmail APIs.

## API Endpoints

### `GET /`
- **Purpose**: A simple health-check endpoint.
- **Returns**: A JSON message indicating that the service is running.

### `POST /register`
- **Purpose**: Handles the one-time user registration and Google OAuth 2.0 flow.
- **Process**:
    1. Receives a temporary authorization code from the frontend after the user grants consent.
    2. Securely exchanges this code for a long-lived **refresh token** and an initial access token.
    3. Verifies the user's identity from the token.
    4. Fetches the user's initial Gmail `historyId` to mark a starting point for email processing.
    5. Stores the user's name, email, encrypted refresh token, and initial `historyId` in the `users` table.
- **Returns**: A success message upon successful registration.

### `POST /saveDocument`
- **Purpose**: Ingests and saves a new document into a user's knowledge base.
- **Request Body**:
    ```json
    {
        "email": "user@example.com",
        "doc_name": "My Document Title",
        "text_content": "The full text content of the document goes here."
    }
    ```
- **Process**:
    1. Validates the total length of the document (enforced server-side).
    2. Generates a 384-dimension vector embedding from the combined title and content.
    3. Stores the document's name, content, and vector embedding in the `documents` table, linked to the user's ID.
- **Returns**: A success or error JSON response.

### `POST /processEmail`
- **Purpose**: The main webhook endpoint intended to be triggered by Google Pub/Sub when a new email arrives for a user.
- **Process (Intended Logic)**:
    1. Receives a notification containing the user's email address.
    2. Fetches the user's refresh token and last known `historyId` from the database.
    3. Generates a short-lived access token to interact with the Gmail API.
    4. Fetches all new emails since the last `historyId`.
    5. For each email, it performs a semantic search against the user's knowledge base to find relevant documents.
    6. Uses the Gemini API, providing the email content and the retrieved documents as context, to generate a draft reply.
    7. Saves the AI-generated response as a draft in the user's Gmail account.
    8. Updates the user's `historyId` in the database to ensure emails are not processed more than once.

### `POST /webhook`
- **Purpose**: A general-purpose endpoint for testing the Gemini API.
- **Request Body**:
    ```json
    {
        "prompt": "Your text prompt for the AI model."
    }
    ```
- **Returns**: The raw text response from the Gemini model.