# Release Process

## Prerequisites

- Write access to the repository
- `PYPI_TOKEN` secret configured in GitHub repo settings
- `ghcr.io` package visibility set to public

## Steps

1. **Prepare the release:**

   ```bash
   git checkout main && git pull
   # Update version in pyproject.toml
   # Update CHANGELOG.md with the new version
   git add -A && git commit -m "chore: prepare vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   ```

2. **Push the tag:**

   ```bash
   git push origin main --tags
   ```

3. **CI does the rest:**

   The [release workflow](.github/workflows/release.yml) automatically:
   - Builds and pushes the Docker image to `ghcr.io`
   - Builds and publishes the Python package to PyPI
   - Creates a GitHub Release with auto-generated changelog

4. **Verify:**

   ```bash
   pip install mcp-fabric==X.Y.Z
   docker pull ghcr.io/deghosal-2026/mcp-fabric:X.Y.Z
   ```

## Versioning

This project follows [Semantic Versioning 2.0](https://semver.org/).
Breaking API changes require a major version bump with deprecation notices
in at least one prior minor release.
