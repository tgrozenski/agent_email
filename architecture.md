# System Architecture

This document outlines the high-level, serverless architecture for the agent-email service deployed on Google Cloud.

```mermaid
graph TD
    subgraph "User-Facing Components"
        User([End User])
        FrontendClient["Frontend Client\n(HTML/CSS/JS, Separate Repo)"]
    end

    subgraph "Google Cloud Platform (GCP)"
        CloudRun["Cloud Run Service\n(FastAPI Container)"]
        Scheduler["Cloud Scheduler"]
        ArtifactRegistry["Artifact Registry\n(Container Image Storage)"]
        SecretManager["Secret Manager"]
        PubSub["Google Pub/Sub"]
        GmailAPI["Gmail API"]
        OAuth["Google OAuth"]
    end

    subgraph "Other External Services"
        AivenDB[("AIVEN PostgreSQL w/ pgvector")]
        Gemini["Gemini API"]
    end

    %% --- High-Level Relationships ---

    User -- "Uses" --> FrontendClient
    FrontendClient -- "API Calls (Login, Docs)" --> CloudRun
    FrontendClient -- "Handles Auth Flow via" --> OAuth

    CloudRun -- "Reads Secrets from" --> SecretManager
    CloudRun -- "Pulls Container Image from" --> ArtifactRegistry
    CloudRun -- "Validates Tokens with" --> OAuth
    CloudRun -- "Manages Users, Docs, Tokens" --> AivenDB
    CloudRun -- "Manages Watch, Reads/Writes Mail" --> GmailAPI
    CloudRun -- "Generates Drafts via" --> Gemini

    Scheduler -- "Triggers Watch Renewal" --> CloudRun
    PubSub -- "Notifies of New Email" --> CloudRun
    GmailAPI -- "Sends Events to" --> PubSub
```
