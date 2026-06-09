from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx

from nixos_deploy_tool.core._base import APIClient
from nixos_deploy_tool.exceptions import APIError, TailscaleAPIError


class TailscaleAPIClient(APIClient):
    BASE_URL = "https://api.tailscale.com/api/v2"

    def __init__(self, client_id: str, client_secret: str, tailnet: str = "-") -> None:
        super().__init__(self.BASE_URL)
        self._client_id = client_id
        self._client_secret = client_secret
        self._tailnet = tailnet
        self._token: str | None = None

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if resp.status_code != 200:
            raise TailscaleAPIError(f"OAuth token failed: {resp.text}")
        data = resp.json()
        self._token = data["access_token"]
        return self._token

    def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._auth_headers()
        resp = httpx.request(method, url, headers=headers, json=json)
        if resp.status_code not in (200, 204):
            raise TailscaleAPIError(f"{method} {path} failed: {resp.text}")
        if resp.status_code == 204:
            return None
        return resp.json()

    def create_auth_key(
        self,
        description: str = "",
        ephemeral: bool = True,
        reusable: bool = False,
        expiry_seconds: int = 3600,
    ) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self._request(
                "POST",
                f"/tailnet/{self._tailnet}/keys",
                json={
                    "capabilities": {
                        "devices": {
                            "create": {
                                "reusable": reusable,
                                "ephemeral": ephemeral,
                                "preauthorized": True,
                            }
                        }
                    },
                    "description": description,
                    "expirySeconds": expiry_seconds,
                },
            ),
        )

    def list_auth_keys(self) -> list[dict[str, Any]]:
        result = self._request("GET", f"/tailnet/{self._tailnet}/keys")
        return cast("list[dict[str, Any]]", result.get("keys", []) if result else [])

    def revoke_auth_key(self, key_id: str) -> None:
        self._request("DELETE", f"/tailnet/{self._tailnet}/keys/{key_id}")

    def device_list(self) -> list[dict[str, Any]]:
        result = self._request("GET", f"/tailnet/{self._tailnet}/devices")
        return cast("list[dict[str, Any]]", result.get("devices", []) if result else [])

    @classmethod
    def from_secret_file(
        cls, client_id: str, secret_file: Path, tailnet: str = "-"
    ) -> TailscaleAPIClient:
        secret = secret_file.read_text().strip()
        return cls(client_id=client_id, client_secret=secret, tailnet=tailnet)
