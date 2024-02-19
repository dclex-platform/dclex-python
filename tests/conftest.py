def pytest_addoption(parser):
    parser.addoption("--test-account-private-key", action="store")
    parser.addoption("--provider-url", action="store")
