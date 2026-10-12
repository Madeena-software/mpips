# Ubuntu Grabber execution evidence

Status: Review Required; independent human-arranged review owns acceptance.
Release status: Not approved. No production deployment, workflow dispatch, server
publication, external binary upload, hospital access, merge or release occurred.

## Immutable identities

- Repository: https://github.com/Madeena-software/mpips
- Feature branch: `feat/ubuntu-grabber-runtime` (non-force pushes only).
- Starting main/origin main: `d645662cd9368c7ba59d9e89a7b033fc3da535b9`.
- Governing task: `.agents/tasks/ubuntu-grabber-runtime.md` @
  `d574d8561de7ae6abd428eddb4a0ce1b645c1ebe` (observed pushed before code changes).
- Implementation: `a52e6f166ee2ecc1136ee1ace1d5aad6f6dbb9f1`, corrected by
  `1fbe51a5146cc21dc116749912f083e049bb433d`; CI/build instructions corrected at
  `2e5441f848b0a47c5211b37fb46fe01b19ceca07` (no runtime code change).
- Final evidence/documentation revision: resolve the immutable HEAD containing this
  evidence record via Git; it does not replace the governing task or implementation.
- Draft PR: https://github.com/Madeena-software/mpips/pull/6
- PR #5 was observed merged; its historical candidate task state was recorded in
  this task, not silently rewritten or self-accepted.

## Implemented and bounded scope

Interface 1 `mpips-runtime` wraps the existing public converter. It accepts explicit
NPZ/gain/manifest/calibration paths; JSON status/exit codes; privately staged
mode-0600 output with no-overwrite commit and cleanup/sanitized failure handling.
It uses the existing local subprocess adapter without a server/launcher daemon.
API/service/imaging/calibration algorithms and protected converter remain unchanged.

The builder snapshots an immutable commit, exports the existing lock, downloads
hash-checked binary dependencies, builds a wheel, performs fresh offline installed
BED/TRX smoke, and creates a target/commit versioned candidate wheelhouse archive
and metadata. Metadata/signature tools use OpenSSL Ed25519, exact authenticated
byte snapshots, compatibility, expiry, sequence and hash/size checks. Publication
plan generation is local only. Real key provisioning/server publication/update
activation are absent and explicitly proposed in the handoff.

The handoff documents hospital-local SIMRS lookup evidence, validated synthetic
reference mapping, patient confirmation, actual timestamps, encounter-versus-
accession behavior, calibration/spacing/view requirements, privacy, offline
processing, proposed HTTPS software updates and Grabber-owned rollback/activation.

## Local checks and commands

Development host: Ubuntu 26.04, x86_64, glibc 2.43, Python 3.12.14.
Observed results are local evidence, not generic Ubuntu or hardware qualification.

| Command / procedure | Observed result |
|---|---|
| `.venv/bin/python -m pytest -q tests/test_conversion_import.py tests/test_converter_protection.py tests/api/test_api_surface.py` (before implementation) | 10 passed, 13 warnings |
| `.venv/bin/python -m pytest -q tests/test_local_runtime.py tests/test_runtime_release.py tests/test_simrs_reference.py tests/test_converter_protection.py` (first implementation) | 43 passed, 3 warnings |
| `.venv/bin/python -m pytest -q tests/test_imager_cli.py tests/test_local_runtime.py tests/test_runtime_release.py tests/test_simrs_reference.py` (correction) | 61 passed, 3 warnings |
| New target-collision and SIMRS-disclosure tests before correction | 2 failed for intended defects; both passed after correction |
| `.venv/bin/python -m pytest -q` (first full run) | 909 passed, 2 skipped, 4 failed, 303 warnings |
| `.venv/bin/python -m pytest -q` (final runtime revision) | 913 passed, 2 skipped, 2 baseline-reproduced directory failures, 302 warnings |
| Full baseline Git archive, same interpreter, recreated pre-existing empty `mpips/engine/calibration` directory, `python -m pytest -q` | 869 passed, 2 skipped, 2 failed, 299 warnings |
| `.venv/bin/python -m pytest -q tests/test_storage.py` after first full failure | 3 passed; full-baseline storage also passed |
| `.venv/bin/python -m black --check mpips tests scripts/build_runtime.py scripts/runtime_release.py scripts/grabber_smoke.py scripts/simrs_manifest_example.py` | 159 files unchanged; passed |
| `.venv/bin/python -m flake8 mpips tests scripts/build_runtime.py scripts/runtime_release.py scripts/grabber_smoke.py scripts/simrs_manifest_example.py` | Passed, no diagnostics |
| `.venv/bin/python -m mypy mpips/runtime.py scripts/build_runtime.py scripts/runtime_release.py scripts/grabber_smoke.py scripts/simrs_manifest_example.py tests/test_local_runtime.py tests/test_runtime_release.py tests/test_simrs_reference.py` | Passed; 8 source files |
| `MYPY_COMMAND='/var/www/mpips/.venv/bin/mypy mpips tests' .venv/bin/python scripts/check_mypy_regressions.py --base-ref d645662cd9368c7ba59d9e89a7b033fc3da535b9 --candidate-ref HEAD` (first implementation and corrected runtime revision) | Both runs: 198 baseline, 198 candidate, 0 new errors |
| `uv lock --check` | Passed; 116 packages |
| `uv export --frozen --no-dev --no-emit-project --format requirements.txt --output-file /tmp/mpips-grabber-runtime-dependencies.txt` and `uv tool run --from pip-audit==2.10.1 pip-audit --require-hashes -r /tmp/mpips-grabber-runtime-dependencies.txt` | No known vulnerabilities in local processing closure |
| `.venv/bin/python scripts/build_runtime.py --commit a52e6f166ee2ecc1136ee1ace1d5aad6f6dbb9f1 --sequence 1 --output /tmp/mpips-grabber-candidates` | Built; fresh offline installed BED/TRX smoke passed |
| `.venv/bin/python scripts/build_runtime.py --commit 1fbe51a5146cc21dc116749912f083e049bb433d --sequence 2 --output /tmp/mpips-grabber-candidates` | Built corrected candidate; fresh offline installed BED/TRX smoke passed |
| Actual corrected tar: sign/verify with ephemeral Ed25519 key; inspect tar/wheel; extract with data filter; fresh venv `pip install --no-index --only-binary=:all: --require-hashes --find-links <bundle>/wheels -r <bundle>/requirements.txt`; installed `mpips-runtime --version` and archived synthetic smoke | All passed; ephemeral keys removed with temporary directory |
| `git diff --check`, changed-file private-key/token pattern scan, manual example/endpoints/CI review | Passed; no secret-pattern findings; examples synthetic; placeholder endpoint example.invalid |
| `sha256sum mpips/conversion/tiff_json_to_dcm.py` and unchanged converter/service/deploy diff | Exact protected hash; no changes |

First full-run failures:

1. `tests/test_imager_cli.py::test_project_scripts_keep_existing_ownership_except_imager`:
   caused by the authorized new entry; updated expectation and verified passing.
2. `tests/test_calibration_dotgrid.py::test_engine_calibration_surfaces_are_retired`.
3. `tests/test_public_boundaries.py::test_engine_package_is_physically_retired`.
   The latter two arise from pre-existing ignored legacy cache directories, which
   create namespace packages despite no tracked legacy engine source. Preserved
   the user's directories; reproduced against baseline with the same empty directory
   structure. A clean Git snapshot does not carry these directories.
4. `tests/test_storage.py::test_s3_direct_upload_and_download`: first full run showed
   a cryptography Rust ML-DSA import AttributeError. Standalone and full baseline
   both passed; the final local full suite also passed storage. No storage/dependency
   changes made to conceal it.

## Actual corrected artifact

Local only, under `/tmp/mpips-grabber-candidates/`:

- Filename: `mpips-0.1.0-1fbe51a5146cc21dc116749912f083e049bb433d-ubuntu26.04-x86_64-py312.tar.gz`.
- Size: `144103198` bytes.
- SHA-256: `dd484e7de28a8d68fc958402c38d5f9cc1030f8c360d0e455bc0b5035bcc64a1`.
- 19 wheels; MPIPS runtime/converter and third-party notices verified present.
- No NPZ, PEM, environment-secret files or legacy engine modules in bundle/wheel.
- Exact target: Ubuntu 26.04 / x86_64 / Python 3.12 / conservative glibc minimum 2.43.
- Release ID includes commit and target; status remains candidate/synthetic-only.
- Verified DICOM: BED `(48,64)`, TRX `(64,48)`, DX presentation SOP class,
  16-bit unsigned MONOCHROME2, synthetic identity/birth/unknown sex,
  empty accession and no private tags.
- No standalone interpreter, apt/deb installation, clinical data or calibration
  training environment is bundled. System Python/venv prerequisite remains explicit.

## Technical review

Separate read-only technical review of `a52e6f1` found a multi-target publication
prefix collision and SIMRS example schema exceptions exposing invalid values.
Both were reproduced with failing tests and corrected in `1fbe51a`.
Follow-up review observed both targeted tests passing and confirmed closure of
those findings. This is technical finding closure, not final acceptance.

## GitHub CI observed on implementation revision

- Existing MPIPS CI: https://github.com/Madeena-software/mpips/actions/runs/38224278040
  failed at **Audit locked dependency closures** before source/tests/container build.
  The unchanged API dependency closure reported 19 known vulnerabilities in
  `anyio 4.13.0`, `urllib3 2.7.0`, `pyjwt 2.13.0`. The local processing closure audit
  is separate and passed. This task does not alter API dependency versions or bypass
  the audit. Dependency remediation needs its own validated scope.
- Initial Ubuntu qualification:
  https://github.com/Madeena-software/mpips/actions/runs/38224278202
  passed runtime audit, Black/Flake8, mypy regression (200 baseline / 198 candidate /
  0 new), and **915 passed / 2 skipped** on clean Ubuntu 24.04 x86_64 / Python
  3.12.15. Bundle build then failed because uv-created `.venv` lacked pip.
  `2e5441f` explicitly supplies pinned pip through `uv run --with pip==26.2.1`;
  no audit/test gate was removed. The corrected run is
  https://github.com/Madeena-software/mpips/actions/runs/38225063938; terminal
  result: **success**, all steps passed. Exact final result is recorded below.
- No production/self-hosted deployment, promotion or release workflow was dispatched.
  CI builds remain GitHub-hosted and no binary artifact upload is configured.

## Files changed

- `.agents/tasks/ubuntu-grabber-runtime.md`
- `.agents/evidence/ubuntu-grabber-runtime.md`
- `.github/workflows/qualify-ubuntu-runtime.yml`
- `mpips/runtime.py`, `pyproject.toml`
- `scripts/build_runtime.py`, `scripts/runtime_release.py`, `scripts/grabber_smoke.py`,
  `scripts/simrs_manifest_example.py`
- `tests/test_local_runtime.py`, `tests/test_runtime_release.py`,
  `tests/test_simrs_reference.py`, `tests/test_imager_cli.py`
- `docs/integration/ubuntu-grabber.md`, `docs/integration/python-import-module.md`,
  `docs/integration/mhcs-dicom-api.md`
- `docs/integration/examples/grabber-manifest.synthetic.json`,
  `docs/integration/examples/simrs-response.synthetic.json`

## Open boundaries

Licensing owner must assess combined ImageJ-style GPL-v2 redistribution; notices
and source do not constitute approval. Infrastructure owner must approve publication,
TLS/auth/signing key/rotation/sequence policy. Hospital owner must confirm real LAN
address/auth/response/date/sex semantics. Clinical owner must approve accession,
identity confirmation and timestamps. Grabber/detector owners must qualify real
hardware, full-size resource limits and updater examination lock/activation/rollback.

Release server endpoints/updater activation are proposed, not implemented. Ubuntu
24.04 support requires actual target CI evidence, and synthetic compatibility is
not real detector/hardware or clinical qualification. Final independent review and
release approval remain separate. Full package distribution is not claimed complete.

## Final local results after correction

The final full run observed **913 passed, 2 skipped, 2 failed** (302 warnings,
194.60 seconds). The only failures are the two legacy-directory cases reproduced
on baseline. Storage passes in this run. Focused checks observed **61 passed**.
Final mypy regression again observed **198 baseline / 198 candidate / 0 new**.

The exact corrected CI command was also executed locally:

```bash
uv run --with pip==26.2.1 python scripts/build_runtime.py \
  --commit 2e5441f848b0a47c5211b37fb46fe01b19ceca07 \
  --sequence 3 --output /tmp/mpips-grabber-candidates
```

Result: built, installed offline into a fresh venv, installed BED/TRX smoke passed.
Latest local artifact is
`mpips-0.1.0-2e5441f848b0a47c5211b37fb46fe01b19ceca07-ubuntu26.04-x86_64-py312.tar.gz`,
size `144103478` bytes, SHA-256
`76985a460937df28edb262267e3e80df25d5e26d7a5ea981920d0a160de307e3`.
Metadata filename, target, size/hash and commit were observed matching. This
additional artifact also remains local-only and candidate/synthetic-only.

## Terminal Ubuntu 24.04 qualification evidence

[Corrected qualification run](https://github.com/Madeena-software/mpips/actions/runs/38225063938)
completed **success** at implementation revision
`2e5441f848b0a47c5211b37fb46fe01b19ceca07`. Observed: runtime audit passed;
Black/Flake8 passed; mypy regression introduced zero diagnostics; **915 passed,
2 skipped** in the clean CI checkout; candidate build, hash-checked offline fresh
installation and installed synthetic BED/TRX smoke all passed. Runner was Ubuntu
24.04 x86_64 with Python 3.12.15. This qualifies the synthetic target boundary,
not a real detector/fleet or clinical deployment. No binary was uploaded.

[Unchanged API CI rerun](https://github.com/Madeena-software/mpips/actions/runs/38225063955)
remains failed at the same API dependency audit. Runtime qualification success
must not be reported as success of that separate existing pipeline.

The final evidence/guide-only commit will naturally start PR checks again. Its
runtime/build code is identical to the successfully qualified immutable revision
above; inspect PR checks for the current-head status. Independent review owns
acceptance, and no merge or release authorization has been asserted.
