#!/bin/bash

# This script sends a mock Pub/Sub message to the /processEmail endpoint.

# The message.data is a base64url-encoded JSON string containing the email address and historyId.
# Decoded: {"emailAddress": "tyler.grozenski@gmail.com", "historyId": "2670240"}
ENCODED_DATA="eyJlbWFpbEFkZHJlc3MiOiAidHlsZXIuZ3JvemVuc2tpQGdtYWlsLmNvbSIsICJoaXN0b3J5SWQiOiAiMjY3MDI0MCJ9"

curl -X POST http://localhost:8000/processEmails \
-H "Content-Type: application/json" \
-d '{
  "message": {
    "data": "'$ENCODED_DATA'",
    "messageId": "2070443601311540",
    "publishTime": "2021-02-26T19:13:55.749Z"
  },
  "subscription": "projects/myproject/subscriptions/mysubscription"
}'
