#!/bin/bash

# This script triggers the renewal of the Gmail watch subscription for all users.
# It requires the INTERNAL_TASK_SECRET environment variable to be set.

if [ -z "$INTERNAL_TASK_SECRET" ]; then
    echo "Error: INTERNAL_TASK_SECRET environment variable is not set."
    exit 1
fi

echo "Triggering Gmail watch renewal..."

curl -X POST http://localhost:8000/tasks/renew-gmail-watch \
-H "Content-Type: application/json" \
-H "x-internal-secret: ${INTERNAL_TASK_SECRET}"

echo "\nDone."

