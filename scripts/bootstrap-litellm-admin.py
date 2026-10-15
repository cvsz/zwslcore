#!/usr/bin/env python3
"""Ensure LiteLLM has a local password-based proxy admin for UI access."""

from __future__ import annotations

import json
import os
import secrets
import string
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from uuid import uuid4


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def login_succeeds(base_url: str, username: str, password: str) -> bool:
    request = Request(
        f"{base_url}/login",
        data=urlencode({"username": username, "password": password}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        response = build_opener(NoRedirect).open(request, timeout=15)
        status = response.status
        location = response.headers.get("Location", "")
    except HTTPError as error:
        status = error.code
        location = error.headers.get("Location", "")
    except URLError:
        return False
    return status == 303 and location.endswith("/ui?login=success")


def post_json(base_url: str, path: str, master_key: str, payload: dict[str, object]) -> None:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {master_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"LiteLLM admin bootstrap failed: HTTP {response.status}")
    except HTTPError as error:
        raise RuntimeError(f"LiteLLM admin bootstrap failed: HTTP {error.code}") from None
    except URLError:
        raise RuntimeError("Could not reach LiteLLM while bootstrapping its UI admin") from None


def account_exists(base_url: str, master_key: str, username: str) -> bool:
    request = Request(
        f"{base_url}/user/info?user_id={username}",
        headers={"Authorization": f"Bearer {master_key}"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            account = json.load(response).get("user_info", {})
            return account.get("user_id") == username and account.get("user_role") == "proxy_admin"
    except (HTTPError, URLError, ValueError):
        return False


def main() -> int:
    env_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env").resolve()
    values = read_env(env_path)
    master_key = values.get("LITELLM_MASTER_KEY", "")
    port = values.get("LITELLM_PORT", "4000")
    if not master_key:
        raise RuntimeError(f"LITELLM_MASTER_KEY is missing from {env_path}")

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(90):
        try:
            with urlopen(f"{base_url}/health/readiness", timeout=3):
                break
        except (HTTPError, URLError):
            time.sleep(2)
    else:
        raise RuntimeError("LiteLLM did not become ready for UI admin bootstrap")

    credentials_dir = Path.home() / ".local" / "share" / "zwslcore"
    credentials_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(credentials_dir, 0o700)
    credentials_path = credentials_dir / "litellm-admin-credentials"

    if credentials_path.exists():
        saved: dict[str, str] = {}
        for line in credentials_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                saved[key] = value
        if saved.get("username") and saved.get("password") and login_succeeds(
            base_url, saved["username"], saved["password"]
        ):
            os.chmod(credentials_path, 0o600)
            print("LiteLLM local password-based proxy admin is ready.")
            return 0
        if saved.get("username") and account_exists(base_url, master_key, saved["username"]):
            os.chmod(credentials_path, 0o600)
            print("LiteLLM proxy admin exists; use its current password if you changed the bootstrap password.")
            return 0
        raise RuntimeError("Saved LiteLLM admin account is missing. Restore it before retrying; no duplicate admin was created.")

    username = f"operator-{uuid4().hex[:12]}@localhost.localdomain"
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    password = "Aa1!" + "".join(secrets.choice(alphabet) for _ in range(40))
    post_json(
        base_url,
        "/user/new",
        master_key,
        {
            "user_id": username,
            "user_email": username,
            "user_role": "proxy_admin",
            "auto_create_key": False,
            "send_invite_email": False,
        },
    )
    post_json(
        base_url,
        "/user/update",
        master_key,
        {
            "user_id": username,
            "user_email": username,
            "user_role": "proxy_admin",
            "password": password,
        },
    )
    if not login_succeeds(base_url, username, password):
        raise RuntimeError("LiteLLM did not accept the bootstrapped admin login")

    temporary_path = credentials_path.with_suffix(".tmp")
    temporary_path.write_text(
        f"username={username}\npassword={password}\n", encoding="utf-8"
    )
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(credentials_path)
    print("Created and verified LiteLLM proxy admin; credentials are in the private local credentials file.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"LiteLLM admin bootstrap failed: {error}", file=sys.stderr)
        raise SystemExit(1)
