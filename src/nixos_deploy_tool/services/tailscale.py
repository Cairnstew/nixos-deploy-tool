from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core.tailscale_api import TailscaleAPIClient
from nixos_deploy_tool.models.config import DeployConfig, TailscaleAuthKeyConfig
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class TailscaleService(BaseService):
    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def __init__(
        self,
        config: DeployConfig,
        client: TailscaleAPIClient | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client

    def _have_credentials(self) -> bool:
        oauth = self.config.tailscale.oauth
        return bool(oauth.client_id and oauth.client_secret_file)

    def _get_client(self) -> TailscaleAPIClient:
        if self._client is not None:
            return self._client
        oauth = self.config.tailscale.oauth
        secret_file = Path(oauth.client_secret_file).expanduser()
        self._client = TailscaleAPIClient.from_secret_file(
            client_id=oauth.client_id,
            secret_file=secret_file,
        )
        return self._client

    def create_auth_key(self, description: str = "", ephemeral: bool = True) -> BaseResult:
        self.logger.info("Creating Tailscale auth key")
        if not self._have_credentials():
            return ErrorResult(message="Tailscale OAuth credentials not configured.")
        try:
            client = self._get_client()
            data = client.create_auth_key(description=description, ephemeral=ephemeral)
            return SuccessResult(
                message="Auth key created.",
                data={"key": data.get("key", "")},
            )
        except Exception as exc:
            return ErrorResult(message=f"Failed to create auth key: {exc}")

    def list_auth_keys(self) -> list[TailscaleAuthKeyConfig]:
        if not self._have_credentials():
            return []
        try:
            client = self._get_client()
            raw_keys = client.list_auth_keys()
            return [
                TailscaleAuthKeyConfig(
                    id=k.get("id", ""),
                    key=k.get("key", ""),
                    description=k.get("description", ""),
                    created=k.get("created", ""),
                    expires=k.get("expires", ""),
                    ephemeral=k.get("ephemeral", False),
                )
                for k in raw_keys
            ]
        except Exception:
            return []

    def revoke_auth_key(self, key_id: str) -> BaseResult:
        self.logger.info("Revoking auth key: %s", key_id)
        if not self._have_credentials():
            return ErrorResult(message="Tailscale OAuth credentials not configured.")
        try:
            client = self._get_client()
            client.revoke_auth_key(key_id)
            return SuccessResult(message=f"Auth key {key_id} revoked.")
        except Exception as exc:
            return ErrorResult(message=f"Failed to revoke auth key: {exc}")

    def status(self) -> BaseResult:
        self.logger.info("Showing Tailscale status")
        if not self._have_credentials():
            return SuccessResult(message="Tailscale status: not configured (no OAuth credentials).")
        try:
            client = self._get_client()
            devices = client.device_list()
            count = len(devices)
            lines = [f"Tailscale: {count} device(s) online"]
            for d in devices:
                name = d.get("name", "?")
                ip = ", ".join(d.get("addresses", []))
                lines.append(f"  {name}  {ip}")
            return SuccessResult(message="\n".join(lines))
        except Exception as exc:
            return ErrorResult(message=f"Failed to get status: {exc}")
