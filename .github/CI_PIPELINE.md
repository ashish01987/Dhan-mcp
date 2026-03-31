# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions for continuous integration and deployment. The pipeline includes linting, testing, and Docker image building.

## Workflows

### 1. **CI Pipeline** (`ci.yml`)
Runs on every push and pull request to `main`, `master`, or `develop` branches.

**Jobs:**
- **Lint**: Code quality checks using flake8, Black, and isort
- **Test**: Unit tests using pytest with coverage reporting
- **Docker**: Verifies Docker image builds successfully
- **Build Status**: Final summary of the pipeline

**Triggers:**
```yaml
on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]
```

### 2. **Docker Publish** (`docker-publish.yml`)
Builds and pushes Docker images to GitHub Container Registry (GHCR).

**Triggers:**
- Push to `main` or `master` branch
- Git tags matching `v*` (e.g., `v1.0.0`)
- Manual workflow dispatch

**Image Tags:**
- `latest` - For default branch (main)
- Branch name - For branch builds
- `vX.Y.Z` - For semantic version tags
- `sha-<commit-hash>` - For every build

## Configuration Files

### `.flake8`
Flake8 linting configuration with:
- Max line length: 120
- Ignored rules: E203, W503
- Excluded directories: `.git`, `__pycache__`, `.venv`, `.claude`

### `pyproject.toml`
Black and isort configuration with:
- Line length: 120
- Target Python: 3.11+
- Profile: Black-compatible imports

### `pytest.ini`
Pytest configuration:
- Test directory: `tests/`
- Asyncio mode: auto
- Markers for integration and slow tests

## Running Tests Locally

### Install test dependencies
```bash
pip install -r requirements.txt pytest pytest-asyncio pytest-cov black flake8 isort
```

### Run all tests
```bash
pytest tests/ -v
```

### Run tests with coverage
```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Run linting
```bash
# Check formatting
black --check .

# Check import sorting
isort --check-only .

# Run flake8
flake8 .
```

### Fix formatting automatically
```bash
# Format with Black
black .

# Fix import sorting
isort .
```

## Writing Tests

Place test files in the `tests/` directory with `test_` prefix:

```python
# tests/test_my_feature.py
import pytest

class TestMyFeature:
    def test_something(self):
        assert True

    @pytest.mark.integration
    def test_integration(self):
        # Integration tests can be skipped with: pytest -m "not integration"
        pass
```

## GitHub Actions Secrets

For the Docker Publish workflow, you may need to configure:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Customizing the Pipeline

### Disable linting checks
In `.github/workflows/ci.yml`, change linting jobs to use `continue-on-error: true` or remove them entirely.

### Add Docker registry credentials
To push to DockerHub instead of GHCR:

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v2
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```

Then update the image name in the `docker-publish.yml` workflow.

### Change Python version
Update `python-version: '3.11'` in the workflow files to target a different Python version.

## Troubleshooting

### Tests failing locally but passing in CI
Check the Python version matches (`3.11+`).

### Docker build fails
- Ensure all required files are in `.dockerignore` compliance
- Check `requirements.txt` has all dependencies
- Review the Dockerfile for any issues

### Linting failures
Run linting locally before pushing:
```bash
black . && isort . && flake8 .
```

## Next Steps

1. **Push to GitHub** - The CI pipeline will trigger automatically
2. **Monitor Actions** - Check the "Actions" tab in GitHub for workflow status
3. **Add more tests** - Expand `tests/` directory with feature-specific tests
4. **Configure notifications** - Set up branch protection rules requiring CI to pass
