"""
conftest.py

Intentionally empty of sys.path manipulation. test_contract_and_performance.py
loads app.py / legacy_app_before.py directly via importlib with unique
module names, to avoid colliding with the unrelated top-level `app` package
used by generated/url_shortener/ when the full repo test suite is collected
in a single pytest session.
"""


