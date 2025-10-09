import unittest
import sys
import os

# Add the project root to the Python path to allow importing from 'src'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_manager import DBManager

class TestDBManagerUnit(unittest.TestCase):
    """Unit tests for DBManager methods."""
    
    @classmethod
    def setUpClass(cls):
        """Set up a single DBManager and connection for all tests."""
        cls.db_manager = DBManager()
        cls.con = cls.db_manager.getcon()

    @classmethod
    def tearDownClass(cls):
        """Close the connection after all tests are done."""
        cls.con.close()

    def setUp(self):
        """Create a fresh cursor for each test."""
        self.cur = self.con.cursor()

    def tearDown(self):
        """Close the cursor after each test."""
        self.cur.close()

    def test_insert_new_user(self):
        """Test inserting a new user."""
        user_email = "insert_test@gmail.com"
        response = self.db_manager.insert_new_user("Tyler", user_email, "842309842309", "historyID123")
        self.assertTrue(response)

        self.cur.execute('SELECT name FROM users WHERE email = %s;', (user_email,))
        res = self.cur.fetchone()
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "Tyler")
        
        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,))
        self.con.commit()

    def test_update_historyID(self):
        """Test updating historyID."""
        user_email = "update_hist@gmail.com"
        self.db_manager.insert_new_user("HistTest", user_email, "token_hist", "historyID123")

        response = self.db_manager.update_historyID(user_email, "newHistoryID")
        self.assertTrue(response)

        self.cur.execute('SELECT history_id FROM users WHERE email = %s;', (user_email,))
        self.assertEqual(self.cur.fetchone()[0], "newHistoryID")

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,))
        self.con.commit()
    
    def test_get_attribute(self):
        """Test getting a specific attribute like refresh token or history_id."""
        user_email = "get_attr@gmail.com"
        self.db_manager.insert_new_user("AttrTest", user_email, "token_secret", "history_attr")

        token = self.db_manager.get_attribute(user_email, "encrypted_refresh_token")
        history_id = self.db_manager.get_attribute(user_email, "history_id")

        self.assertEqual(token, "token_secret")
        self.assertEqual(history_id, "history_attr")

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,))
        self.con.commit()

    def test_insert_document(self):
        """Test inserting a document using user_email."""
        user_email = "document_test@gmail.com"
        self.db_manager.insert_new_user("DocTest", user_email, "token123", "hist123")
        
        doc_name = "My Test Document"
        text_content = "This is the content of the test document."

        # Act: Pass the email directly to the refactored method
        response = self.db_manager.insert_document(user_email, doc_name, text_content)
        self.assertTrue(response)

        # Verify the document was inserted correctly
        self.cur.execute("SELECT d.document_name, d.content, d.embedding FROM documents d JOIN users u ON d.user_id = u.user_id WHERE u.email = %s;", (user_email,))
        res = self.cur.fetchone()
        
        self.assertIsNotNone(res)
        db_doc_name, db_content, db_embedding = res
        
        self.assertEqual(db_doc_name, doc_name)
        self.assertEqual(db_content, text_content)
        self.assertIsNotNone(db_embedding)
        self.assertEqual(len(db_embedding.strip('[]').split(',')), 384)

        # Ensure oversize documents are rejected
        self.assertRaises(ValueError, self.db_manager.insert_document, user_email, "BigDoc", "A" * 5000)

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,)) # Documents are deleted by cascade
        self.con.commit()
    
    def test_top_k_results(self):
        """Test retrieving top-k results using user_email."""
        user_email = "topk_test@example.com"
        self.db_manager.insert_new_user("TopKTest", user_email, "token_topk", "hist_topk")
        
        self.db_manager.insert_document(user_email, "Doc1", "birds, dogs, and pets.")
        self.db_manager.insert_document(user_email, "Doc2", "This content is about cars, bikes, and vehicles.")
        self.db_manager.insert_document(user_email, "Doc3", "This content is pasta, italian food, meatballs, ect.")

        # Act: Call get_top_k_results with user_email
        pet_results = self.db_manager.get_top_k_results("I love my dog and my pet bird.", 1, user_email)
        self.assertEqual(len(pet_results), 1)
        self.assertEqual(pet_results[0]['content'], "birds, dogs, and pets.")

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,))
        self.con.commit()

    def test_delete_document(self):
        """Test deleting a single document."""
        user_email = "delete_test@example.com"
        self.db_manager.insert_new_user("DeleteTest", user_email, "token_del", "hist_del")
        self.db_manager.insert_document(user_email, "DocToDelete", "This document will be deleted.")
        
        self.cur.execute("SELECT d.doc_id FROM documents d JOIN users u ON d.user_id = u.user_id WHERE u.email = %s;", (user_email,))
        doc_id = self.cur.fetchone()[0]

        response = self.db_manager.delete_document(doc_id)
        self.assertTrue(response)

        self.cur.execute("SELECT * FROM documents WHERE doc_id = %s;", (doc_id,))
        self.assertIsNone(self.cur.fetchone())

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s;', (user_email,))
        self.con.commit()

    def test_get_all_users_for_watch(self):
        """Test retrieving all users for the watch renewal."""
        user1_email, user1_token = "watch_user1@example.com", "token_watch1"
        user2_email, user2_token = "watch_user2@example.com", "token_watch2"
        
        self.db_manager.insert_new_user("WatchUser1", user1_email, user1_token, "hist_w1")
        self.db_manager.insert_new_user("WatchUser2", user2_email, user2_token, "hist_w2")

        result = self.db_manager.get_all_users_for_watch()
        result_tuples = {tuple(row) for row in result}
        
        self.assertIn((user1_email, user1_token), result_tuples)
        self.assertIn((user2_email, user2_token), result_tuples)

        # Cleanup
        self.cur.execute('DELETE FROM users WHERE email = %s OR email = %s;', (user1_email, user2_email))
        self.con.commit()

if __name__ == "__main__":
    unittest.main()
