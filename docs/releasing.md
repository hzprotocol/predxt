# Releasing

`predxt` uses SemVer. Release tags use the `vX.Y.Z` format.

## First release

1. Confirm the version in `pyproject.toml` and `src/predxt/__init__.py`.
2. Update `CHANGELOG.md`.
3. Run local validation:

   ```bash
   uv sync --group dev
   uv run ruff check .
   uv run pytest -q
   uv build
   ```

4. Push `main`.
5. Create and push a tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

6. The release workflow builds distributions, creates a GitHub release, publishes
   to TestPyPI, then publishes to PyPI when Trusted Publishing is configured.

## PyPI

Use PyPI Trusted Publishing for GitHub Actions. Configure the TestPyPI and PyPI
projects named `predxt` to trust this repository and the `release.yml` workflow.

If Trusted Publishing is not configured for the first release, build artifacts
locally and publish manually from a controlled maintainer environment.
