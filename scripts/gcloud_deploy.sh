docker build -t us-west2-docker.pkg.dev/agentemail-468518/agent-email-repo/agent-email:v1.1 .
docker push us-west2-docker.pkg.dev/agentemail-468518/agent-email-repo/agent-email:v1.1
gcloud run deploy email-service \
--image="us-west2-docker.pkg.dev/agentemail-468518/agent-email-repo/agent-email:v1.1" \
--platform=managed \
--memory=1Gi \
--region=us-west2 \
--service-account="592589126466-compute@developer.gserviceaccount.com" \
--set-secrets="AIVEN_PASSWORD=AIVEN_PASSWORD:latest,DATABASE_URL=DATABASE_URL:latest,GEMINI_AGENT_EMAIL=GEMINI_AGENT_EMAIL:latest,GOOGLE_CREDENTIALS=GOOGLE_CREDENTIALS:latest,INTERNAL_TASK_SECRET=INTERNAL_TASK_SECRET:latest,GCP_PUBSUB_TOPIC_NAME=GCP_PUBSUB_TOPIC_NAME:latest" \
--allow-unauthenticated
