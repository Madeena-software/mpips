from pathlib import Path

ROOT = Path(__file__).parents[1]
UV_DIGEST = "sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945"


def test_deployment_builds_use_persistent_separate_buildkit_caches():
    api = (ROOT / "Dockerfile").read_text()
    worker = (ROOT / "docker/Dockerfile.worker").read_text()
    workflow = (ROOT / ".github/workflows/deploy-internal-beta.yml").read_text()

    for dockerfile, extra in ((api, "service"), (worker, "imager")):
        assert "ghcr.io/astral-sh/uv:latest" not in dockerfile
        assert f"ghcr.io/astral-sh/uv@{UV_DIGEST} AS uv" in dockerfile
        assert "RUN --mount=type=cache" in dockerfile
        assert "sharing=locked" in dockerfile
        assert f"--extra {extra}" in dockerfile
        assert dockerfile.index("RUN apt-get") < dockerfile.index("COPY --from=uv")
        assert dockerfile.index("uv sync") < dockerfile.index("COPY mpips")

    assert "id=mpips-api-uv" in api
    assert "id=mpips-worker-uv" in worker
    assert "docker buildx build" in workflow
    assert workflow.count('build_image "mpips-') == 2
    assert "--load" in workflow
    assert '--cache-from "type=local' in workflow
    assert '--cache-to "type=local' in workflow
    assert "mode=max" in workflow
    assert 'CACHE_ROOT="${HOME}/.cache/mpips-buildkit"' in workflow
    assert 'API_CACHE="$CACHE_ROOT/api"' in workflow
    assert 'WORKER_CACHE="$CACHE_ROOT/worker"' in workflow
    assert "mpips-production-cache" in workflow
    assert "--driver docker-container" in workflow
    assert "index.json" in workflow
    assert "mpips-api:$MPIPS_VERSION" in workflow
    assert "mpips-npz-worker:$MPIPS_VERSION" in workflow
    assert "docker image inspect" in workflow
    assert "--no-cache" not in workflow
    assert "type=gha" not in workflow
    assert "docker push" not in workflow
    assert "group: mpips-internal-beta" in workflow
    assert "actions/setup-python@v5" in workflow
    assert "python -m pip install uv" in workflow
    assert (
        "uv sync --frozen --extra service --extra dev --extra npz-worker --extra imager"
        in workflow
    )


def test_buildkit_bootstrap_has_bounded_retry_without_builder_recreation():
    workflow = (ROOT / ".github/workflows/deploy-internal-beta.yml").read_text()

    assert "bootstrap_builder()" in workflow
    start = workflow.index("bootstrap_builder()")
    bootstrap = workflow[start : workflow.index("          build_image", start)]
    assert "local max_attempts=3" in bootstrap
    assert 'for attempt in $(seq 1 "$max_attempts")' in bootstrap
    assert 'docker buildx inspect --bootstrap "$BUILDER"' in bootstrap
    assert "sleep 10" in bootstrap
    assert "sleep 30" in bootstrap
    assert 'echo "BuildKit bootstrap failed after $max_attempts attempts"' in bootstrap
    assert "return 1" in bootstrap
    assert "docker buildx rm" not in bootstrap
    assert "docker buildx create" not in bootstrap
