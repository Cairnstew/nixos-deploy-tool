from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core.age import AgeRunner
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.repositories.agenix_catalog import AgenixCatalog
from nixos_deploy_tool.services.base import BaseService


class SecretService(BaseService):
    def __init__(
        self,
        config: DeployConfig,
        catalog: AgenixCatalog | None = None,
        age: AgeRunner | None = None,
    ) -> None:
        super().__init__(config)
        flake_root = Path(config.flake_root) if config.flake_root else Path.cwd()
        self._catalog = catalog or AgenixCatalog(flake_root, config.secrets_dir)
        self._age = age or AgeRunner(age_bin=config.paths.age_bin or "age")

    def list_secrets(self) -> list[dict[str, object]]:
        try:
            age_files = self._catalog.list_age_files()
            secret_list: list[dict[str, object]] = [
                {"name": f.name, "path": str(f)} for f in age_files
            ]
            nix_secrets = self._catalog.parse_secrets_nix()
            for name, data in nix_secrets.items():
                if data and isinstance(data, dict):
                    secret_list.append({"name": name, **data})
            return secret_list
        except Exception:
            return []

    def decrypt(self, name: str) -> BaseResult:
        self.logger.info("Decrypting secret: %s", name)
        try:
            age_files = self._catalog.list_age_files()
            matches = [f for f in age_files if f.name == name or name in f.name]
            if not matches:
                return ErrorResult(message=f"Secret '{name}' not found.")
            for f in matches:
                plaintext = self._age.decrypt(f)
                out = f.with_suffix("")
                out.write_text(plaintext)
                self.logger.info("Decrypted %s -> %s", f, out)
            return SuccessResult(message=f"Secret {name} decrypted.")
        except Exception as exc:
            return ErrorResult(message=f"Decrypt failed: {exc}")

    def rekey(self) -> BaseResult:
        self.logger.info("Rekeying all secrets")
        try:
            age_files = self._catalog.list_age_files()
            if not age_files:
                return SuccessResult(message="No secrets to rekey.")
            new_key = self._age.keygen()
            for f in age_files:
                plaintext = self._age.decrypt(f)
                encrypted = self._age.encrypt(recipient=new_key, plaintext=plaintext)
                f.write_text(encrypted)
            return SuccessResult(message=f"Secrets rekeyed ({len(age_files)} files).")
        except Exception as exc:
            return ErrorResult(message=f"Rekey failed: {exc}")
