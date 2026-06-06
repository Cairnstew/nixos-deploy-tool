from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import httpx

from nixos_deploy_tool.exceptions import TailscaleAPIError


class TailscaleAPIClient:
    BASE_URL = "https://api.tailscale.com/api/v2"

    def __init__(self, client_id: str, client_secret: str, tailnet: str = "-") -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._tailnet = tailnet
        self._logger = logging.getLogger(self.__class__.__name__)
        self._token: str | None = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            f"{self.BASE_URL}/oauth/token",
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

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def create_auth_key(
        self,
        description: str = "",
        ephemeral: bool = True,
        reusable: bool = False,
        expiry_seconds: int = 3600,
    ) -> dict[str, Any]:
        resp = httpx.post(
            f"{self.BASE_URL}/tailnet/{self._tailnet}/keys",
            headers=self._headers(),
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
        )
        if resp.status_code != 200:
            raise TailscaleAPIError(f"Create key failed: {resp.text}")
        return cast("dict[str, Any]", resp.json())

    def list_auth_keys(self) -> list[dict[str, Any]]:
        resp = httpx.get(
            f"{self.BASE_URL}/tailnet/{self._tailnet}/keys",
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise TailscaleAPIError(f"List keys failed: {resp.text}")
        return cast("list[dict[str, Any]]", resp.json().get("keys", []))

    def revoke_auth_key(self, key_id: str) -> None:
        resp = httpx.delete(
            f"{self.BASE_URL}/tailnet/{self._tailnet}/keys/{key_id}",
            headers=self._headers(),
        )
        if resp.status_code not in (200, 204):
            raise TailscaleAPIError(f"Revoke key failed: {resp.text}")

    def device_list(self) -> list[dict[str, Any]]:
        resp = httpx.get(
            f"{self.BASE_URL}/tailnet/{self._tailnet}/devices",
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise TailscaleAPIError(f"Device list failed: {resp.text}")
        return cast("list[dict[str, Any]]", resp.json().get("devices", []))

    @classmethod
    def from_secret_file(
        cls, client_id: str, secret_file: Path, tailnet: str = "-"
    ) -> TailscaleAPIClient:
        secret = secret_file.read_text().strip()
        return cls(client_id=client_id, client_secret=secret, tailnet=tailnet)
