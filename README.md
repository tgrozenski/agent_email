# System Architecture

## 1. Overall Architecture

This system is designed using a thin-client architecture. The majority of the logic and processing is handled by a serverless cloud function, while the client-side is responsible for initial setup and user interaction.

The flow is as follows:
1.  The user visits the client page and authenticates via OAuth.
2.  The client page programmatically sets up a Pub/Sub topic for the user's Gmail account to push email notifications to the Cloud Function (serverless function).
3.  When a new email arrives, Gmail pushes a notification to the Pub/Sub topic.
4.  The Pub/Sub topic triggers the cloud function.
5.  The cloud function processes the email, queries a knowledge base for context, and interacts with the Gemini API.
6.  Gemini creates a draft which is place in the user's gmail drafts, where they can choose to send it or not.

## 2. Components

### 2.1. Client Page

The client page is the user-facing component of the system. We will use Firebase to host a React frontend. This makes sense for the design given how straightforward the client needs to be, it will be interacting primarily with APIs and over network.

**Responsibilities:**

*   **Authentication:** Initiates the OAuth 2.0 flow to obtain the necessary permissions from the user.
    *   **Permissions Required:**
        *   `https://www.googleapis.com/auth/gmail.readonly`
        *   `https://www.googleapis.com/auth/gmail.compose`
*   **Pub/Sub Setup:** Programmatically creates a new Google Cloud Pub/Sub topic for the user's Gmail account. This topic will receive notifications for new emails.
*   **Webhook Configuration:** Configures the Pub/Sub topic to push notifications to the cloud function's URL.
*   **Knowledge Base Initialization:** Creates a new knowledge base for the user, identified by their email address.
*   **Database Setup:** Initializes a document store in MongoDB, hosted on Google Cloud, for the user.

### 2.2. Cloud Function (Webhook)

This is a serverless function hosted on Google Cloud that acts as the webhook endpoint for the Pub/Sub topic. This will be written in python for simplicity and use of the great libraries present for genAI.


**Responsibilities:**

*   **Receives Notifications:** Ingests push notifications from the Google Cloud Pub/Sub topic, which are triggered by new emails in the user's Gmail account.

*   **Data Retrieval:**
    *   Retrieves the full email content from Gmail using the information in the Pub/Sub message.
    *   Queries the user-specific knowledge base stored in MongoDB to gather relevant context for processing the email.

*   **AI Processing:** Interacts with the Gemini API to perform the core logic of the application. Gemini will query the knowledgebase (mongoDB) for relevant context and attempt to make a reply. The reply will be saved as a draft for the user to optionally send.

## 3. Data Storage

*   **MongoDB:** A MongoDB instance hosted on Google Cloud is used as the document store for the knowledge base. Each user's data will be stored in a collection where the documents are identified by the user's email address.

## 4. Authentication

*   **OAuth 2.0:** User authentication and authorization are handled via Google's OAuth 2.0.
*   **User Identification:** The user's email address will be used as the unique identifier for their data and resources.

## 5. TBD

*   How is the user's knowledge base structured in MongoDB? Is it a separate database per user or a collection with a `userId` field?