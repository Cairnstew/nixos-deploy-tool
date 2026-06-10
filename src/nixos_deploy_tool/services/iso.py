from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core.age import AgeRunner
from nixos_deploy_tool.core.flake import FlakeIntrospector
from nixos_deploy_tool.core.iso_builder import ISOBuilder
from nixos_deploy_tool.models.config import DeployConfig, ISOConfig, SecretInjection
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.repositories.agenix_catalog import AgenixCatalog
from nixos_deploy_tool.services.base import BaseService


class ISOService(BaseService):
    def __init__(
        self,
        config: DeployConfig,
        builder: ISOBuilder | None = None,
        flake: FlakeIntrospector | None = None,
        age: AgeRunner | None = None,
    ) -> None:
        super().__init__(config)
        if not config.flake_root:
            raise RuntimeError("ISOService: DeployConfig.flake_root must be set")
        flake_root = Path(config.flake_root)
        self._flake_root = flake_root
        self._builder = builder or ISOBuilder(nix_bin=config.paths.nixos_anywhere_bin or "nix")
        self._flake = flake or FlakeIntrospector(flake_root)
        self._age = age or AgeRunner(age_bin=config.paths.age_bin or "age")

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def list_isos(self) -> list[ISOConfig]:
        raw = self._flake.list_iso_configs()
        return [ISOConfig(name=str(item["name"]), flake_attr=str(item["attr"])) for item in raw]

    def build(self, name: str) -> BaseResult:
        self.logger.info("Building ISO: %s", name)
        try:
            out_path = self._builder.build(
                flake_root=self._flake_root,
                iso_attr=name,
            )
            return SuccessResult(message=f"ISO {name} built at {out_path}.")
        except Exception as exc:
            return ErrorResult(message=f"ISO build failed: {exc}")

    def rotate_keys(self, name: str) -> BaseResult:
        self.logger.info("Rotating keys for ISO: %s", name)
        catalog = AgenixCatalog(self._flake_root, self.config.secrets_dir)
        age_files = catalog.list_age_files()
        if not age_files:
            return SuccessResult(message=f"No age files to rekey for {name}.")
        for f in age_files:
            try:
                plaintext = self._age.decrypt(f)
                self._age.encrypt(recipient=name, plaintext=plaintext)
            except Exception as exc:
                return ErrorResult(message=f"Rekey failed for {f}: {exc}")
        return SuccessResult(message=f"Keys rotated for {name} ({len(age_files)} files).")

    def info(self, name: str) -> ISOConfig | None:
        isos = self.list_isos()
        for iso in isos:
            if iso.name == name or iso.flake_attr == name:
                return iso
        return None

    def inject_secrets(self, iso_name: str, secrets: list[SecretInjection]) -> BaseResult:
        self.logger.info("Injecting %d secrets into ISO %s", len(secrets), iso_name)
        if not secrets:
            return SuccessResult(message=f"No secrets to inject into {iso_name}.")
        for s in secrets:
            try:
                encrypted = self._age.encrypt(
                    recipient=s.name,
                    plaintext=s.age_source.read_text(),
                )
                target = Path(s.target_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(encrypted)
            except Exception as exc:
                return ErrorResult(message=f"Secret injection failed for {s.name}: {exc}")
        return SuccessResult(message=f"Secrets injected into {iso_name}.")
