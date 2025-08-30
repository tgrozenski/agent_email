from sqlalchemy import pool
import pg8000
import os

AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]

class DBManager:
    mypool : pool.QueuePool = None

    def __init__(self):
        # pooling to manage potential concurrent connections
        self.mypool = pool.QueuePool(self.getcon, max_overflow=10, pool_size=5)

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
                'INSERT INTO "user" (name, email, encrypted_refresh_token, history_id) '
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
                UPDATE "user"
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
    
    """
    Returns the refresh token for a user identified by their email.
    Returns None if user not found or on error.
    """
    def get_refresh_token(self, user_email: str) -> str:

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT encrypted_refresh_token FROM "user" WHERE email = %s;', (user_email,)
            )
            res = cur.fetchone()
            if res:
                return res[0]
            else:
                return None
        except Exception as e:
            print("Database operation failed in get_refresh_token.")
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