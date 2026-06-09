from __future__ import annotations

from nixos_deploy_tool.core.key_store import KeyStore
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class PrepareService(BaseService):
    def __init__(
        self,
        config: DeployConfig,
        keystore: KeyStore | None = None,
    ) -> None:
        super().__init__(config)
        self._keystore = keystore or KeyStore()

    def prepare(self, hostname: str) -> BaseResult:
        try:
            if self._keystore.exists(hostname):
                pubkey = self._keystore.public_key(hostname)
                return SuccessResult(
                    data={"pubkey": pubkey, "newly_generated": False},
                    message=f"Keypair already exists for '{hostname}'.\nPublic key: {pubkey}",
                )

            privkey_path, pubkey = self._keystore.generate(hostname)
            lines = [
                f"Generated host keypair for '{hostname}'.",
                f"Public key: {pubkey}",
                "",
                "Next steps:",
                f"1. Add this public key to keys.groups.systems in common.nix",
                "2. Run: nix develop .#secrets && agenix-manager rekey",
                "3. Commit the rekeyed .age files",
                f"4. Run: nixos-deploy deploy run {hostname} --addr <addr> --extra-args \"--disko-mode mount\"",
            ]
            return SuccessResult(
                data={"pubkey": pubkey, "newly_generated": True, "privkey_path": str(privkey_path)},
                message="\n".join(lines),
            )
        except Exception as exc:
            return ErrorResult(message=f"Prepare failed for '{hostname}': {exc}")
