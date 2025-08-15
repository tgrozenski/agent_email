from sqlalchemy import pool
import pg8000
import os

AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]

class DBManager:
    mypool : pool.QueuePool

    def __init__(self):
        # pooling to manage potential concurrent connections
        self.mypool = pool.QueuePool(self.getcon, max_overflow=10, pool_size=5)

    
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
    
    def insert_new_user(self, user_name, user_email, refresh_token, historyID) -> bool:
        if not user_email or not refresh_token:
            return False

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO "user" (name, email, encrypted_refresh_token, history_id) '
                'VALUES (%s, %s, %s, %s) '
                'ON CONFLICT (email) DO NOTHING',
                (user_name, user_email, refresh_token, historyID)
            )
            conn.commit()
        except Exception as e:
            return False
        finally:
            if conn:
                conn.close()

        return True

    """
    Takes in a refresh token and returns an access token
    """
    def get_refresh_token(self, user_email: str) -> str:

        conn = None
        try:
            conn = self.mypool.connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT refresh_token FROM "user"'
                'WHERE email = %s',
                (user_email)
            )
            res = cur.fetchone()
            if res:
                return res[0]
            else:
                return None
        except Exception as e:
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