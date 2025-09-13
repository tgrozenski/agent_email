from sqlalchemy import pool
from fastembed import TextEmbedding
import pg8000
import os

AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]
# Ensure our content fits into RAG vector limit (384 dims)
MAX_DOCUMENT_LENGTH = 2000

class DBManager:
    mypool : pool.QueuePool = None
    embedding_model: TextEmbedding = None

    def __init__(self):
        # pooling to manage potential concurrent connections
        self.mypool = pool.QueuePool(self.getcon, max_overflow=10, pool_size=5)
        # Load the embedding model once when the DBManager is initialized for efficiency
        self.embedding_model = TextEmbedding()

    """
    Inserts a new user into the database. Returns True if successful, False otherwise.
    Does not insert if user with email already exists.
    """
    def insert_new_user(self, name, user_email, refresh_token, historyID) -> bool:
        if not user_email or not refresh_token:
            print("user_email or refresh_token are None.")
            return False

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO users (name, email, encrypted_refresh_token, history_id) '
                'VALUES (%s, %s, %s, %s) '
                'ON CONFLICT (email) DO NOTHING',
                (name, user_email, refresh_token, historyID)
            )
            conn.commit()
        except Exception as e:
            print("Exception trying to insert new user into db.")
            print(e)
            return False
        finally:
            if conn:
                conn.close()

        return True

    """
    Updates the historyID for a user identified by their email. Returns True if successful, False
    """
    def update_historyID(self, user_email: str, historyID: str) -> bool:
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE users
                    SET history_id = %s
                    WHERE email = %s;
                """, (historyID, user_email)
            )
            conn.commit()
        except Exception as e:
            print("Database operation failed.")
            return False
        finally:
            if conn:
                conn.close()

        return True

    def get_attribute(self, user_email: str, attribute: str) -> bool:
        """
        Fetch an attribute from the db with a given user email
        """
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                f'SELECT {attribute} FROM users WHERE email = \'{user_email}\';'
            )

            res = cur.fetchone()
            if res:
                return res[0]
            else:
                return None
        except Exception as e:
            print("Database operation failed in last historyID.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()
    
    def insert_document(self, user_id: str, doc_name: str, text_content: str) -> bool:
        """
        Insert a given document into the database, generates a embedding for RAG to insert.
        """

        # Enforce document limits server-side
        doc = doc_name + "\n" + text_content
        if len(doc) > MAX_DOCUMENT_LENGTH:
            raise ValueError("Document too long, must be under 2000 characters., got " + str(len(doc)))

        embeddings_list = list(self.embedding_model.embed([doc]))
        embedding = embeddings_list[0]

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO documents' \
                '(user_id, document_name, embedding, content)' \
                'VALUES (%s, %s, %s, %s);',
                (user_id, doc_name, str(embedding.tolist()), text_content)
            )
            conn.commit()
        except Exception as e:
            print("Database operation failed in insert_document.")
            print(e)
            return False
        finally:
            if conn:
                conn.close()
        
        return True
    
    def get_documents(self, user_id: str) -> list[dict] | None:
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT doc_id, document_name, content FROM documents WHERE user_id = %s;',
                (user_id,)
            )
            results = cur.fetchall()
            documents = []
            for row in results:
                documents.append({
                    "id": row[0],
                    "name": row[1],
                    "content": row[2]
                })
            return documents
        except Exception as e:
            print("Database operation failed in get_documents.")
            print(e)
            return None

    def get_top_k_results(self, query: str, k: int, user_id: str) -> list[dict] | None:
        """
        Generates an embedding for the query and returns the top k most similar documents for a user.
        May return None in the event of a database error.
        """
        # 1. Generate the embedding for the user's query.
        query_embedding = list(self.embedding_model.embed([query]))[0]
        query_vector_str = str(query_embedding.tolist())

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            sql = """
                SELECT
                    doc_id,
                    document_name,
                    content,
                    1 - (embedding <=> %s) AS similarity
                FROM
                    documents
                WHERE
                    user_id = %s
                ORDER BY
                    embedding <=> %s
                LIMIT %s;
            """
            cur.execute(sql, (query_vector_str, user_id, query_vector_str, k))
            results = cur.fetchall()
            
            formatted_results = []
            for row in results:
                formatted_results.append({
                    "id": row[0],
                    "name": row[1],
                    "content": row[2],
                    "similarity": round(row[3], 4)
                })
            return formatted_results

        except Exception as e:
            print("Database operation failed in get_top_k_results.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def getcon():
        con = pg8000.dbapi.connect(
            user="avnadmin",
            password=AIVEN_PASSWORD,
            host="pg-38474cd-agent-email.e.aivencloud.com",
            port=17757,
            database="defaultdb"
        )
        return con