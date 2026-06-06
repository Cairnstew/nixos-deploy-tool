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
def test_module_option_log_level() -> None:
    expr = """
      let
        nixpkgs = (builtins.getFlake (toString ./.)).inputs.nixpkgs;
        lib = nixpkgs.lib;
        module = (builtins.getFlake (toString ./.)).nixosModules.default;
        evaled = lib.evalModules {
          modules = [ module { services.nixos-deploy-tool.enable = true; } ];
        };
        s = evaled.config.services.nixos-deploy-tool.settings;
        json = builtins.fromJSON (builtins.toJSON s);
      in builtins.typeOf json.logLevel
    """
    result = subprocess.run(
        ["nix", "eval", "--expr", expr],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "string" in result.stdout
