"""End-to-end verification script for the MPIPS staging update server."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def _request(
    url: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
) -> tuple[int, dict[str, Any] | None, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers.items())
            try:
                data = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                data = None
            return resp.status, data, resp_headers, body
    except urllib.error.HTTPError as err:
        body = err.read()
        resp_headers = dict(err.headers.items())
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = None
        return err.code, data, resp_headers, body


def run_checks(base_url: str, token: str) -> bool:
    base = base_url.rstrip("/")
    all_ok = True

    print(f"=== MPIPS Staging Update Server Verification: {base} ===")

    # 1. Health check
    status, data, _, _ = _request(f"{base}/mpips/staging/health")
    if status == 200 and data and data.get("status") == "ok":
        print(f"  [PASS] 1. Health endpoint (200 OK): {data}")
    else:
        print(f"  [FAIL] 1. Health endpoint returned {status}: {data}")
        all_ok = False

    # 2. Unauthenticated latest.json check (must return 401)
    status, data, _, _ = _request(f"{base}/mpips/staging/latest.json")
    if status == 401 and data and data.get("error", {}).get("code") == "unauthorized":
        print("  [PASS] 2. Unauthenticated latest.json rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 2. Unauthenticated latest.json returned {status}: {data}")
        all_ok = False

    # 3. Invalid token latest.json check (must return 401)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/latest.json",
        headers={"Authorization": "Bearer invalid-token-xyz"},
    )
    if status == 401 and data and data.get("error", {}).get("code") == "unauthorized":
        print("  [PASS] 3. Invalid token rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 3. Invalid token returned {status}: {data}")
        all_ok = False

    # 4. Incompatible platform (must return 422)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/latest.json?platform=windows-x86_64",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status == 422:
        print("  [PASS] 4. Incompatible platform rejected (422 Unprocessable Content)")
    else:
        print(f"  [FAIL] 4. Incompatible platform returned {status}: {data}")
        all_ok = False

    # 5. Authenticated latest.json check (200 OK, no_release or available)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/latest.json",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status == 200 and data and data.get("schema_version") == 1:
        release_status = data.get("status")
        print(
            f"  [PASS] 5. Authenticated latest.json (200 OK, status={release_status})"
        )
        if release_status == "available":
            release_id = data.get("release_id")
            expected_sha = data.get("sha256")
            expected_size = data.get("size_bytes")
            print(f"         Available release: {release_id} (SHA: {expected_sha})")

            # 6. Authenticated download URL check
            dl_status, dl_data, _, _ = _request(
                f"{base}/mpips/staging/releases/{release_id}/download",
                headers={"Authorization": f"Bearer {token}"},
            )
            if dl_status == 200 and dl_data and "download_url" in dl_data:
                dl_url = dl_data["download_url"]
                print("  [PASS] 6. Presigned download URL issued successfully")

                # 7. Download binary from presigned URL and verify integrity
                try:
                    with urllib.request.urlopen(dl_url, timeout=30) as dl_resp:
                        bin_bytes = dl_resp.read()
                    actual_sha = hashlib.sha256(bin_bytes).hexdigest()
                    if actual_sha == expected_sha and len(bin_bytes) == expected_size:
                        print(
                            "  [PASS] 7. Downloaded binary integrity verified "
                            f"(SHA-256 match, size={len(bin_bytes)} bytes)"
                        )
                    else:
                        print(
                            "  [FAIL] 7. Binary integrity mismatch: "
                            f"expected={expected_sha}, actual={actual_sha}"
                        )
                        all_ok = False
                except Exception as exc:
                    print(f"  [FAIL] 7. Download failed: {exc}")
                    all_ok = False
            else:
                print(f"  [FAIL] 6. Download endpoint returned {dl_status}: {dl_data}")
                all_ok = False
        else:
            print(
                "         Channel status is 'no_release' "
                "(no production binary promoted yet, G10 NOT RELEASED)"
            )
    else:
        print(f"  [FAIL] 5. Authenticated latest.json returned {status}: {data}")
        all_ok = False

    # 8. Unauthenticated download endpoint rejected (401)
    status, data, _, _ = _request(
        f"{base}/mpips/staging/releases/test-release/download"
    )
    if status == 401:
        print("  [PASS] 8. Unauthenticated download rejected (401 Unauthorized)")
    else:
        print(f"  [FAIL] 8. Unauthenticated download returned {status}: {data}")
        all_ok = False

    # 9. Nonexistent release download returns 404
    status, data, _, _ = _request(
        f"{base}/mpips/staging/releases/nonexistent-release-xyz/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    if status == 404:
        print("  [PASS] 9. Nonexistent release download rejected (404 Not Found)")
    else:
        print(f"  [FAIL] 9. Nonexistent release returned {status}: {data}")
        all_ok = False

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="https://ip.mhcsgo.cloud",
        help="Base URL of the update server (default: https://ip.mhcsgo.cloud)",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Staging reader authentication token",
    )
    args = parser.parse_args()
    success = run_checks(args.base_url, args.token)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
