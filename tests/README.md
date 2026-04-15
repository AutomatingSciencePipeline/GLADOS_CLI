# GLADOS CLI Test Suite

This directory has unit and integration tests for the GLADOS CLI.

## Directories

- The unit directory has an automated test suite that deals with the business logic of the CLI, with the data subdirectory holding files that allow the tests to run properly. The test file can be run with the command `python tests/unit/glados_cli_tests.py` from the project root.
- The integration directory tests the flow of API calls to the NextJS endpoints of GLADOS. It has a partially automated test suite; it requires a tester to first authenticate via the CLI and then ensure they have no experiments named Test AddNums. The test file can be run with the command `python tests/integration/glados_workflow_tests.py` from the project root.