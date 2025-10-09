from sqlalchemy import pool
from fastembed import TextEmbedding
import pg8000
import os
import ssl

AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]
# Ensure our content fits into RAG vector limit (384 dims)
MAX_DOCUMENT_LENGTH = 2000

class DBManager:
    mypool : pool.QueuePool = None
    embedding_model: TextEmbedding = None

    def __init__(self):
        # pooling to manage potential concurrent connections
        try:
            self.mypool = pool.QueuePool(self.getcon, max_overflow=10, pool_size=5)
        except Exception as e:
            print(f"Failed connecting, Exception: {e}")
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

    def get_attribute(self, user_email: str, attribute: str) -> str | None:
        """
        Fetch an attribute from the db with a given user email.
        Note: The attribute name is controlled internally and not by user input.
        """
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            # Use parameterized query for user_email to prevent SQL injection
            sql = f'SELECT {attribute} FROM users WHERE email = %s;'
            cur.execute(sql, (user_email,))

            res = cur.fetchone()
            if res:
                return res[0]
            else:
                return None
        except Exception as e:
            print(f"Database operation failed while getting attribute {attribute}.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()

    def insert_document(
            self,
            user_email: str,
            doc_name: str,
            text_content: str,
            doc_id: str = None
        ) -> bool:
        """
        Insert a given document into the database using the user's email.
        If doc_id is provided, it will update the existing document instead.
        """
        # Enforce document limits server-side
        doc = doc_name + "\n" + text_content
        if len(doc) > MAX_DOCUMENT_LENGTH:
            raise ValueError(f"Document too long, must be under {MAX_DOCUMENT_LENGTH} characters., got {len(doc)}")

        embeddings_list = list(self.embedding_model.embed([doc]))
        embedding = embeddings_list[0]
        embedding_str = str(embedding.tolist())

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            if doc_id:
                cur.execute(
                    'UPDATE documents SET embedding = %s, content = %s WHERE doc_id = %s;',
                    (embedding_str, text_content, doc_id)
                )
            else:
                sql = """
                    INSERT INTO documents (user_id, document_name, embedding, content)
                    SELECT
                        u.user_id,
                        %s,
                        %s,
                        %s
                    FROM
                        users u
                    WHERE
                        u.email = %s;
                """
                params = (doc_name, embedding_str, text_content, user_email)
                cur.execute(sql, params)
            conn.commit()
        except Exception as e:
            print("Database operation failed in insert_document.")
            print(e)
            return False
        finally:
            if conn:
                conn.close()
        return True

    def delete_document(self, doc_id: str) -> bool:
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM documents WHERE doc_id = %s;",
                (doc_id,)
            )
            conn.commit()
        except Exception as e:
            print("Database operation failed in delete_document.")
            print(e)
            return False
        return True

    def get_documents(self, user_email: str, limit: int, offset: int, content: bool = True) -> list[dict] | None:
        """
        Fetch all documents for a given user by email.
        """
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()

            columns = "d.doc_id, d.document_name"
            if content:
                columns += ", d.content"

            sql = f"""
                SELECT {columns}
                FROM documents d
                JOIN users u ON u.user_id = d.user_id
                WHERE u.email = %s
                ORDER BY d.document_name ASC
                LIMIT %s OFFSET %s;
            """
            cur.execute(sql, (user_email, limit, offset))

            results = cur.fetchall()
            documents = []
            for row in results:
                doc = {"id": row[0], "name": row[1]}
                if content:
                    doc["content"] = row[2]
                documents.append(doc)
            return documents
        except Exception as e:
            print("Database operation failed in get_documents.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()

    def get_document_by_id(self, doc_id: str) -> dict | None:
        """
        Fetch a single document by its ID. May return None if not found or on error.
        """
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT doc_id, document_name, content FROM documents WHERE doc_id = %s;',
                (doc_id,)
            )
            result = cur.fetchone()
            if result:
                return {"id": result[0], "name": result[1], "content": result[2]}
            else:
                return None
        except Exception as e:
            print("Database operation failed in get_document_by_id.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()

    def get_top_k_results(self, query: str, k: int, user_email: str) -> list[dict] | None:
        """
        Generates an embedding for the query and returns the top k most similar documents for a user.
        """
        query_embedding = list(self.embedding_model.embed([query]))[0]
        query_vector_str = str(query_embedding.tolist())

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            sql = """
                SELECT
                    d.doc_id,
                    d.document_name,
                    d.content,
                    1 - (d.embedding <=> %s) AS similarity
                FROM
                    documents d
                JOIN users u ON d.user_id = u.user_id
                WHERE
                    u.email = %s
                ORDER BY
                    d.embedding <=> %s
                LIMIT %s;
            """
            params = (query_vector_str, user_email, query_vector_str, k)
            cur.execute(sql, params)
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

    def get_all_users_for_watch(self) -> list[[str, str]]: #[name, encrypted_refresh_token]
        """
        This method retrieves all users and their refresh_tokens
        Necessary for renew gmail watch
        """
        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute('SELECT email, encrypted_refresh_token FROM users')
            return list(cur.fetchall())
        except Exception as e:
            print("Database operation failed in get_all_users_for_watch.")
            print(e)
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def getcon():
        ssl_context = ssl.create_default_context(cafile="ca.pem")
        con = pg8000.dbapi.connect(
            user="avnadmin",
            password=AIVEN_PASSWORD,
            host="pg-38474cd-agent-email.e.aivencloud.com",
            port=17757,
            database="defaultdb",
            ssl_context=ssl_context
        )
        return con
