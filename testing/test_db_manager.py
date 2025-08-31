import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_manager import DBManager

class TestDBManagerUnit(unittest.TestCase):
    db_manager = DBManager()
    con = db_manager.getcon()
    cur = con.cursor()

    """Unit tests for DBManager methods."""
    def test_insert_new_user(self):
        """Test inserting a new user."""

        # Act
        response = self.db_manager.insert_new_user("Tyler", "bob@gmail.com", "842309842309", "historyID123")

        # Assert
        self.assertTrue(response)

        self.cur.execute('SELECT name FROM "user" where name = \'Tyler\';')
        res = self.cur.fetchall()
        assert res[0][0] == "Tyler"
        
        self.cur.execute('SELECT * FROM "user"')
        self.assertEqual(len(self.cur.fetchall()[0]), 5) # 5 columns in user table

        # Cleanup
        self.cur.execute('DELETE FROM "user" where name = \'Tyler\';')
        self.con.commit()

    def test_update_historyID(self):
        """Test updating historyID."""

        # Arrange
        # Insert a test user
        self.db_manager.insert_new_user("Tyler", "bob@gmail.com", "842309842309", "historyID123")

        # Act
        response = self.db_manager.update_historyID("bob@gmail.com", "newHistoryID")

        self.assertTrue(response)

        # Assert
        self.cur.execute(
            'SELECT history_id FROM "user" where email = \'bob@gmail.com\';'
            )

        self.assertEqual(
            self.cur.fetchone()[0],
            "newHistoryID"
        )

        # Cleanup
        self.cur.execute('DELETE FROM "user" where name = \'Tyler\';')
        self.con.commit()
    
    def test_get_refresh_token(self):
        """Test getting refresh token."""

        # Arrange
        # Insert a test user
        self.db_manager.insert_new_user("Tyler", "bob@gmail.com", "842309842309", "historyID123")

        # Act
        token = self.db_manager.get_attribute(
            attribute="encrypted_refresh_token",
            user_email="bob@gmail.com"
        )

        # Assert
        self.assertEqual(token, "842309842309")

        # Cleanup
        self.cur.execute('DELETE FROM "user" where email = \'bob@gmail.com\';')
        self.con.commit()

    def test_get_history_id(self):
        """Test getting history_id."""

        # Arrange
        # Insert a test user
        self.db_manager.insert_new_user("Tyler", "bob@gmail.com", "842309842309", "historyID123")

        # Act
        token = self.db_manager.get_attribute(
            attribute="history_id",
            user_email="bob@gmail.com"
        )

        # Assert
        self.assertEqual(token, "historyID123")

        # Cleanup
        self.cur.execute('DELETE FROM "user" where email = \'bob@gmail.com\';')
        self.con.commit()


if __name__ == "__main__":
    unittest.main()