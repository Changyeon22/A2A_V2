# -*- coding: utf-8 -*-
"""
Pytest configuration: ensure project root is on sys.path for imports like `agents.*` and `configs.*`.
"""
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
