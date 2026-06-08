from __future__ import annotations

import subprocess

import pytest


@pytest.mark.nix
def test_module_evaluates() -> None:
    result = subprocess.run(
        ["nix", "eval", ".#nixosModules.default", "--apply", "builtins.typeOf"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "lambda" in result.stdout


@pytest.mark.nix
def test_module_settings_accepts_freeform_keys() -> None:
    """Verify settings option accepts undeclared keys via freeformType.

    Evaluates the option declaration (not the full config) to confirm
    that freeform keys like auto_detect_disko are accepted.
    """
    expr = """
      let
        nixpkgs = (builtins.getFlake (toString ./.)).inputs.nixpkgs;
        module = (builtins.getFlake (toString ./.)).nixosModules.default;
        nixos = nixpkgs.lib.nixosSystem {
          system = builtins.currentSystem;
          modules = [
            module
            {
              services.nixos-deploy-tool.enable = true;
              services.nixos-deploy-tool.settings = {
                auto_detect_disko = true;
                skip_disko = false;
                disko_mode = null;
                default_extra_args = ["--phases" "kexec,install,reboot"];
              };
            }
          ];
        };
        s = nixos.config.services.nixos-deploy-tool.settings;
      in
        if ! builtins.hasAttr "auto_detect_disko" s then "auto_detect_disko:missing"
        else if s.auto_detect_disko != true then "auto_detect_disko:wrong"
        else if s.skip_disko != false then "skip_disko:wrong"
        else if ! builtins.hasAttr "default_extra_args" s then "default_extra_args:missing"
            else if builtins.length s.default_extra_args != 2 then "default_extra_args:wrong_length"
        else if ! builtins.hasAttr "disko_mode" s then "disko_mode:missing"
        else "all_keys_present"
    """
    result = subprocess.run(
        ["nix", "eval", "--impure", "--expr", expr],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "all_keys_present" in result.stdout
