# Ensure the test user exists in the database (avoids violating foreign key constraint)
psql 'postgres://avnadmin:AVNS_00YSqjFuLb40X7iDCNq@pg-38474cd-agent-email.aivencloud.com:17757/defaultdb?sslmode=require' \
-c "INSERT INTO users (email, name, history_id, encrypted_refresh_token) VALUES ('testuser@example.com', 'Test User', 'history123', 'encryptedtoken123') ON CONFLICT (email) DO NOTHING;"

echo "Testing /saveDocument with Authorization header..."
curl -X POST http://localhost:8000/saveDocument \
-H "Content-Type: application/json" \
-H "Authorization: Bearer FAKE_TOKEN" \
-d '{ \
    "doc_name": "Meeting Notes Q3", \
    "text_content": "This document contains the summary of our third quarter planning meeting and action items." \
}'
echo "\n"

echo "Testing /saveDocument without Authorization header (should fail)..."
curl -X POST http://localhost:8000/saveDocument \
-H "Content-Type: application/json" \
-d '{ \
    "doc_name": "Favorite colors", \
    "text_content": "My favorite colors are blue, green, and red. I also like yellow occasionally." \
}'
echo "\n"

echo "Testing /getDocuments with Authorization header..."
curl -X GET http://localhost:8000/getDocuments \
-H "Authorization: Bearer FAKE_TOKEN"
echo "\n"

echo "Testing /getDocuments without Authorization header (should fail)..."
curl -X GET http://localhost:8000/getDocuments
echo "\n"
