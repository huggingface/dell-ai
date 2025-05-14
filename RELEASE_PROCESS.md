# Release Process

This document outlines the process for creating and publishing new releases of the Dell AI SDK.

## Prerequisites

1. Install development dependencies including `bump2version`:
   ```bash
   uv pip install -e ".[dev]"
   ```

## Creating a New Release

### 1. Test the Package

Before releasing, manually test the package to ensure everything works as expected:

```bash
# Run tests
pytest

# Check code quality
flake8 dell_ai tests

# Verify the package builds correctly
uv build --no-sources
```

### 2. Update Version and Create Tag

We use a tag-based release process. To release a new version:

1. Make sure your local `main` branch is up to date:
   ```bash
   git checkout main
   git pull
   ```

2. Create a "version bump" branch:
   ```bash
   git checkout -b bump-version-X.Y.Z
   ```

3. Update the version using `bump2version`:
   ```bash
   # For a patch release (0.0.4 -> 0.0.5)
   bump2version patch

   # For a minor release (0.0.4 -> 0.1.0)
   bump2version minor

   # For a major release (0.0.4 -> 1.0.0)
   bump2version major
   ```

   This will:
   - Update version in `dell_ai/__init__.py`
   - Update version in `pyproject.toml`
   - Update version in `README.md`
   - Create a git commit with these changes
   - Create a version tag

4. Push the branch and create a PR:
   ```bash
   git push -u origin bump-version-X.Y.Z
   ```

5. After PR review and merge to main, push the tag:
   ```bash
   git checkout main
   git pull
   git push --tags
   ```

### 3. Automated Release Process

Once the tag is pushed, GitHub Actions will automatically:
1. Run tests to verify the package
2. Build the package using UV
3. Publish to PyPI
4. Create a GitHub release with generated release notes

## Handling Additional Changes

### If Additional PRs Land After Your Version Bump

If other PRs are merged to main after your version bump PR but before you push the tag:

1. Update your local main and move the tag to the latest commit:
   ```bash
   git checkout main
   git pull  # Get all the latest changes

   # Delete the old tag
   git tag -d vX.Y.Z

   # Create a new tag at the current (latest) commit
   git tag vX.Y.Z

   # Push the tag
   git push --tags
   ```

This ensures the release includes all changes merged to main, not just your version bump.

### If You Want to Include Specific PRs in a Release

For coordinated releases:

1. Create your version bump PR but don't merge it immediately
2. Wait for all desired changes to be merged to main
3. Merge your version bump PR last
4. Immediately push the tag after the version bump PR is merged

## Manual Release (Fallback)

If you need to release manually:

```bash
rm -rf dist/
uv build --no-sources
uv publish --token $PYPI_TOKEN
```

## Troubleshooting

If the release automation fails:
1. Check the GitHub Actions logs for error details
2. Fix any issues in a new commit
3. Delete the failed tag locally and remotely:
   ```bash
   git tag -d vX.Y.Z
   git push --delete origin vX.Y.Z
   ```
4. Create and push a new tag once fixes are in place 