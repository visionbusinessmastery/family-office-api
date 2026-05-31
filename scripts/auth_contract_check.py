import argparse
import sys
import urllib.error
import urllib.request

def request_status(base_url: str, path: str, token: str | None = None, raw_auth: str | None = None):
    headers = {}
    if raw_auth is not None:
        headers["Authorization"] = raw_auth
    elif token is not None:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{base_url.rstrip('/')}{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def assert_status(label: str, result, expected_status: int):
    status, body = result
    ok = status == expected_status
    marker = "OK" if ok else "FAIL"
    print(f"{marker} {label}: {status}")
    if not ok:
        print(body[:500])
    return ok


def main():
    parser = argparse.ArgumentParser(description="White Rock auth contract smoke test.")
    parser.add_argument(
        "--base-url",
        default="https://family-office-api-n4sv.onrender.com",
        help="Backend base URL.",
    )
    parser.add_argument(
        "--valid-token",
        default=None,
        help="Optional valid JWT to test authenticated /auth/me.",
    )
    parser.add_argument(
        "--expired-token",
        default=None,
        help="Optional expired JWT to verify that expired sessions return 401.",
    )
    args = parser.parse_args()

    checks = [
        ("public /health", request_status(args.base_url, "/health"), 200),
        ("protected /portfolio no token", request_status(args.base_url, "/portfolio/"), 401),
        (
            "protected /portfolio invalid token",
            request_status(args.base_url, "/portfolio/", token="INVALID_TOKEN_123"),
            401,
        ),
        (
            "protected /portfolio malformed raw token",
            request_status(args.base_url, "/portfolio/", raw_auth="eyJhbGciOi"),
            401,
        ),
        (
            "protected /portfolio malformed prefix",
            request_status(args.base_url, "/portfolio/", raw_auth="Token eyJhbGciOi"),
            401,
        ),
        ("protected /auth/me no token", request_status(args.base_url, "/auth/me"), 401),
    ]

    if args.valid_token:
        checks.append(
            (
                "protected /auth/me valid token",
                request_status(args.base_url, "/auth/me", token=args.valid_token),
                200,
            )
        )

    if args.expired_token:
        checks.append(
            (
                "protected /auth/me expired token",
                request_status(args.base_url, "/auth/me", token=args.expired_token),
                401,
            )
        )

    failed = [
        label
        for label, response, expected in checks
        if not assert_status(label, response, expected)
    ]

    if failed:
        print("\nFailed checks:")
        for label in failed:
            print(f"- {label}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
