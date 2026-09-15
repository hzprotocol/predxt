# Releasing

`predxt` uses SemVer. Release tags use the `vX.Y.Z` format.

## Prepare the release

1. Update the version in `pyproject.toml` and `src/predxt/__init__.py` together.
   Run `uv lock --offline` and check that only the local `predxt` package version
   changed in `uv.lock`.
2. Add a versioned entry to `CHANGELOG.md`. Update installation requirements in
   the README, first-run docs, and LLM guidance when new commands require the release.
3. Run local validation:

   ```bash
   uv sync --group dev
   uv run ruff check .
   uv run mypy
   uv run pytest -q -s
   uv build
   uv run twine check dist/*
   uv run mkdocs build --strict
   ```

4. Install the built wheel in a fresh environment and run `predxt demo --json`
   from outside the repository. Confirm its version matches the release and
   its output is marked synthetic. Test `predxt explore polymarket` against the
   public API when first-run behavior changes; record any external API failure
   separately from the local tests.
5. Open the release PR and verify CI on the final commit. Keep dependency upgrades
   separate from a version-only release preparation.

## Publish

After the release PR is merged and CI passes on `main`:

1. Confirm PyPI Trusted Publishing is configured:

   - PyPI project name: `predxt`
   - Owner: `hzprotocol`
   - Repository: `predxt`
   - Workflow: `release.yml`
   - Environment: `pypi`

2. From a clean checkout of the released `main`, create and push the tag matching
   the package version. The tag push starts the release workflow:

   ```bash
   release_version=$(uv run python -c "import predxt; print(predxt.__version__)")
   git tag "v${release_version}"
   git push origin "v${release_version}"
   ```

3. The release workflow builds distributions first. The publish job waits for
   the GitHub `pypi` environment approval, then creates the GitHub release and
   publishes to PyPI with Trusted Publishing.

4. Confirm the GitHub release and exact PyPI version exist. Install that version
   in a fresh environment and run the offline demo. Check that the published
   documentation shows the matching first-run instructions before sharing them.

## PyPI

Use PyPI Trusted Publishing for GitHub Actions. Configure the PyPI project named
`predxt` to trust this repository and the `release.yml` workflow with the
`pypi` environment.

If Trusted Publishing is not configured for the first release, build artifacts
locally and publish manually from a controlled maintainer environment.
