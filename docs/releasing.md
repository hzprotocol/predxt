# Releasing

`predxt` uses SemVer. Release tags use the `vX.Y.Z` format.

## First release

1. Confirm the version in `pyproject.toml` and `src/predxt/__init__.py`.
2. Update `CHANGELOG.md`.
3. Run local validation:

   ```bash
   uv sync --group dev
   uv run ruff check .
   uv run mypy
   uv run pytest -q -s
   uv build
   uv run twine check dist/*
   ```

4. Push `main`.
5. Confirm PyPI Trusted Publishing is configured:

   - PyPI project name: `predxt`
   - Owner: `hzprotocol`
   - Repository: `predxt`
   - Workflow: `release.yml`
   - Environment: `pypi`

6. Create and push a tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

7. The release workflow builds distributions first. The publish job waits for
   the GitHub `pypi` environment approval, then creates the GitHub release and
   publishes to PyPI with Trusted Publishing.

## PyPI

Use PyPI Trusted Publishing for GitHub Actions. Configure the PyPI project named
`predxt` to trust this repository and the `release.yml` workflow with the
`pypi` environment.

If Trusted Publishing is not configured for the first release, build artifacts
locally and publish manually from a controlled maintainer environment.
