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

        self.cur.execute('SELECT name FROM users where name = \'Tyler\';')
        res = self.cur.fetchall()
        assert res[0][0] == "Tyler"
        
        self.cur.execute('SELECT * FROM users')
        self.assertEqual(len(self.cur.fetchall()[0]), 5) # 5 columns in user table

        # Cleanup
        self.cur.execute('DELETE FROM users where name = \'Tyler\';')
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
            'SELECT history_id FROM users where email = \'bob@gmail.com\';'
            )

        self.assertEqual(
            self.cur.fetchone()[0],
            "newHistoryID"
        )

        # Cleanup
        self.cur.execute('DELETE FROM users where name = \'Tyler\';')
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
        self.cur.execute('DELETE FROM users where email = \'bob@gmail.com\';')
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
        self.cur.execute('DELETE FROM users where email = \'bob@gmail.com\';')
        self.con.commit()

    def test_insert_document(self):
        """Test inserting a document."""
        # Arrange
        # Insert a test user to get a user_id
        user_email = "document_test@gmail.com"
        self.db_manager.insert_new_user("DocTest", user_email, "token123", "hist123")
        
        # Get the id of the inserted user
        self.cur.execute('SELECT user_id FROM users WHERE email = %s;', (user_email,))
        user_id = self.cur.fetchone()[0]

        doc_name = "My Test Document"
        text_content = "This is the content of the test document."

        # Act
        response = self.db_manager.insert_document(user_id, doc_name, text_content)

        # Assert
        self.assertTrue(response)

        # Verify the document was inserted correctly
        self.cur.execute('SELECT document_name, content, embedding FROM documents WHERE user_id = %s;', (user_id,))
        res = self.cur.fetchone()
        
        self.assertIsNotNone(res)
        db_doc_name, db_content, db_embedding = res
        
        self.assertEqual(db_doc_name, doc_name)
        self.assertEqual(db_content, text_content)
        self.assertIsNotNone(db_embedding)

        # Parse embedding string to list of float
        embedding_list = [float(x) for x in db_embedding.strip('[]').split(',')]
        self.assertEqual(len(embedding_list), 384)

        # Ensure oversize documents are rejected
        self.assertRaises(ValueError, self.db_manager.insert_document, user_id, "BigDoc", "A" * 5000)

        # Cleanup
        self.cur.execute('DELETE FROM documents WHERE user_id = %s;', (user_id,))
        self.cur.execute('DELETE FROM users WHERE user_id = %s;', (user_id,))
        self.con.commit()
    
    def test_top_k_results(self):
        """
        Test retrieving top-k results based on similarity.
        Test is extremely slow, run in isolation.
        """
        # Arrange
        self.cur.execute(
            "INSERT INTO users" \
            "(email, name, history_id, encrypted_refresh_token)" \
            "VALUES ('testuser@example.com', 'Test User', 'history123', 'encryptedtoken123')" \
            "ON CONFLICT (email) DO NOTHING;"
        )
        user_id = self.db_manager.get_attribute("testuser@example.com", "user_id")
        self.db_manager.insert_document(user_id, "Doc1", "birds, dogs, and pets.")
        self.db_manager.insert_document(user_id, "Doc2", "This content is about cars, bikes, and vehicles.")
        self.db_manager.insert_document(user_id, "Doc3", "This content is pasta, italian food, meatballs, ect.")

        # Act
        # dead match for first entry
        pet_results = self.db_manager.get_top_k_results("I love my dog and my pet bird.", 1, user_id)
        # This is close to the italian food entry
        food_results = self.db_manager.get_top_k_results("I enjoy dinners that include spagetti and noodles, also garlic bread.", 1, user_id)
        # Similar words to vehicles entry
        vehicle_results = self.db_manager.get_top_k_results("In order to be a mechanic you need to understand wheels, tires, and other transportation methods", 1, user_id)

        # Assert
        self.assertEqual(len(pet_results), 1)
        self.assertIsNotNone(pet_results[0])
        self.assertEqual(pet_results[0]['content'], "birds, dogs, and pets.")

        self.assertEqual(len(food_results), 1)
        self.assertIsNotNone(food_results[0])
        self.assertEqual(food_results[0]['content'], "This content is pasta, italian food, meatballs, ect.")

        self.assertEqual(len(vehicle_results), 1)
        self.assertIsNotNone(vehicle_results[0])
        self.assertEqual(vehicle_results[0]['content'], "This content is about cars, bikes, and vehicles.")

    def test_delete_documents(self):
        """Test deleting all documents for a user."""
        # Arrange
        self.db_manager.insert_document(user_id="31",
                                        doc_name="DocToDelete",
                                        text_content="This document will be deleted.")
        self.cur.execute("SELECT doc_id FROM documents WHERE document_name = 'DocToDelete';")
        doc_id = self.cur.fetchone()[0] 

        # Act
        self.db_manager.delete_document(doc_id)

        # Assert
        self.cur.execute("SELECT * FROM documents WHERE document_name = 'DocToDelete';")
        res = self.cur.fetchone()
        self.assertIsNone(res)

    def test_get_all_users(self):
        expected = [
            ['testuser@example.com', 'encryptedtoken123'],
            ['tyler.grozenski@gmail.com', '1//06VDn2eK1oQf3CgYIARAAGAYSNwF-L9Ir9Z8oRJ0PPqDJEP2iSv9sMLeMi4FsNid8DVMo1qjg1hC_EswNKDKjbzh8JvWbvjhT_JU']
        ]
        result = self.db_manager.get_all_users_for_watch()
        
        # print("expected", expected)
        # print("result: ", result)
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main().test_get_all_users()
