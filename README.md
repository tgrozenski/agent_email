# Agent-Assisted Email Architecture

This document outlines the architecture for an email processing agent that automatically drafts responses to incoming emails.

The system uses a secure, multi-user architecture built on Google Cloud. It separates the client-side authentication flow from the event-driven email processing flow.

## Components

1.  **Frontend Application**
    *   **Responsibility:** Handles all user-facing interaction for the one-time OAuth 2.0 consent flow.
    *   **Function:** It initiates the Google Sign-In process and receives a temporary authorization code from Google upon user consent. It immediately sends this code to the backend's `/register` endpoint. **Crucially, it never handles sensitive tokens.**

2.  **Backend Application (FastAPI)**
    *   **Responsibility:** The secure, trusted core of the system. It is the only component that interacts with the database and Secret Manager.
    *   **Endpoints:**
        *   `/register`: A secure endpoint that receives the authorization code, exchanges it for a refresh token, and orchestrates storing the user's credentials and data.
        *   `/pubSub`: A secure endpoint that serves as the target for the Pub/Sub push subscription. This is the main email processing logic invoked by new messages.

3.  **Google Cloud SQL for PostgreSQL**
    *   **Responsibility:** A unified, single database system for all application data, including user metadata and the user-specific knowledge base.
    *   **Function:**
        *   **User Metadata:** Acts as the central directory for mapping incoming emails to the correct user. It stores information like the user's Google ID, email address, and the resource name of their corresponding secret in Secret Manager. It **does not** store the actual OAuth tokens.
        *   **Knowledge Base:** Stores each user's knowledge base documents. It leverages PostgreSQL's advanced features like the `JSONB` data type for storing semi-structured documents and Full-Text Search for efficient, intelligent searching of the document content. This consolidation simplifies the architecture by avoiding the need for a separate document database.

4.  **Google Cloud Pub/Sub**
    *   **Responsibility:** A real-time messaging service that decouples the Gmail API from the Backend Application.
    *   **Function:** It receives push notifications from the Gmail API when a new email arrives. It uses a **Push Subscription** to forward these notifications immediately to the backend's `/pubSub` endpoint, triggering the processing logic in real-time.

5.  **Google Gmail API**
    *   **Responsibility:** The primary interface for interacting with the user's mailbox.
    *   **Function:** It provides the OAuth 2.0 infrastructure, allows the backend to fetch email content, create drafts, and sends push notifications to Pub/Sub. All interactions are initiated by the trusted backend.