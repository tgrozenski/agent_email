# Agent-Assisted Email Architecture

This document outlines the architecture for an email processing agent that automatically drafts responses to incoming emails.

The system uses a secure, multi-user architecture built on Google Cloud. It separates the client-side authentication flow from the event-driven email processing flow.

## Architectural Diagram

The architecture is divided into two main processes: a one-time user onboarding flow and a recurring, event-driven email processing flow.

## Components

1.  **Frontend Application**
    *   **Responsibility:** Handles all user-facing interaction for the one-time OAuth 2.0 consent flow.
    *   **Function:** It initiates the Google Sign-In process and receives a temporary authorization code from Google upon user consent. It immediately sends this code to the backend's `/register` endpoint. **Crucially, it never handles sensitive tokens.**

2.  **Backend Application (FastAPI)**
    *   **Responsibility:** The secure, trusted core of the system. It is the only component that interacts with the database and Secret Manager.
    *   **Endpoints:**
        *   `/register`: A secure endpoint that receives the authorization code, exchanges it for a refresh token, and orchestrates storing the user's credentials and data.
        *   **Pub/Sub Triggered Function:** The main email processing logic that is invoked by new messages on the Pub/Sub topic.

3.  **Google Cloud SQL**
    *   **Responsibility:** A relational database (e.g., PostgreSQL) that stores non-sensitive user metadata.
    *   **Function:** It acts as the central directory for mapping incoming emails to the correct user. It stores information like the user's Google ID, email address, and the resource name of their corresponding secret in Secret Manager. It **does not** store the actual OAuth tokens.

4.  **Google Secret Manager**
    *   **Responsibility:** A secure vault for storing highly sensitive credentials.
    *   **Function:** It stores each user's encrypted OAuth Refresh Token. Access to these secrets is tightly controlled via IAM and is only granted to the Backend Application's service account.

5.  **Google Cloud Pub/Sub**
    *   **Responsibility:** A real-time messaging service that decouples the Gmail API from the Backend Application.
    *   **Function:** It receives push notifications from the Gmail API when a new email arrives and triggers the backend processing function.

6.  **Google Gmail API**
    *   **Responsibility:** The primary interface for interacting with the user's mailbox.
    *   **Function:** It provides the OAuth 2.0 infrastructure, allows the backend to fetch email content, create drafts, and sends push notifications to Pub/Sub. All interactions are initiated by the trusted backend.
