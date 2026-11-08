import unittest
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from tests.test_mcp_server_extensions import TestMCPServerExtensions

suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPServerExtensions)
runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
