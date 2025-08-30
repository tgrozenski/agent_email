import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mail import Email, get_unprocessed_emails

class TestMailUnit(unittest.TestCase):
    """Unit tests for mail.py."""