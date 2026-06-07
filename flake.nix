{
  description = "NixOS deploy tool — CLI/TUI for ISOs, secrets, and nixos-anywhere deployments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$REPO_ROOT";
      };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;

          baseSet = pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
          };

          pythonSet = baseSet.overrideScope (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
            ]
          );

          editablePythonSet = pythonSet.overrideScope editableOverlay;
        in
        {
          inherit pythonSet editablePythonSet python pkgs;
        }
      );
    in
    {
      packages = forAllSystems (
        system:
        let p = pythonSets.${system}; in
        {
          default = p.pkgs.callPackage ./nix/default.nix {
            inherit (p) pythonSet pkgs;
            inherit workspace pyproject-nix;
          };
        }
      );

      apps = forAllSystems (system:
        {
          default = {
            type = "app";
            program = "${self.packages.${system}.default}/bin/nixos-deploy";
          };
          build-iso = {
            type = "app";
            program = "${self.packages.${system}.default}/bin/nixos-deploy";
          };
          deploy = {
            type = "app";
            program = "${self.packages.${system}.default}/bin/nixos-deploy";
          };
          deploy-wizard = {
            type = "app";
            program = "${self.packages.${system}.default}/bin/nixos-deploy";
          };
        }
      );

      devShells = forAllSystems (system:
        let
          p = pythonSets.${system};
          virtualenv = p.editablePythonSet.mkVirtualEnv "dev-env" workspace.deps.all;
        in
        {
          default = p.pkgs.mkShell {
            packages = [ virtualenv p.pkgs.uv ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = "${p.python.interpreter}";
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
            '';
          };

          bootstrap = p.pkgs.mkShell {
            packages = [ p.pkgs.python312 p.pkgs.uv ];
          };
        }
      );

      overlays.default = final: prev: {
        nixos-deploy-tool = pythonSets.${final.stdenv.hostPlatform.system}.pythonSet."nixos-deploy-tool";
      };

      nixosModules.default = { pkgs, ... }: {
        imports = [ ./nix/module.nix ];
        services.nixos-deploy-tool.package = lib.mkForce self.packages.${pkgs.system}.default;
      };

      homeManagerModules.default = import ./nix/home-module.nix;

      checks = forAllSystems (system:
        let
          p = pythonSets.${system};
          pkgs = p.pkgs;
          pkg = p.pythonSet."nixos-deploy-tool";
        in
        {
          build = pkg;

          venv = p.pythonSet.mkVirtualEnv "app-env" { nixos-deploy-tool = [ ]; };

          format = pkgs.runCommand "check-format" {
            nativeBuildInputs = [ pkgs.nixpkgs-fmt ];
          } ''
            nixpkgs-fmt --check ${./.}
            touch "$out"
          '';

          app-help = pkgs.runCommand "app-help" {
            nativeBuildInputs = [ self.packages.${system}.default ];
          } ''
            nixos-deploy --help > "$out" 2>&1
            grep -q "Usage" "$out" || {
              echo "FAIL: --help did not produce Usage output"
              exit 1
            }
          '';

          module-eval = pkgs.runCommand "module-eval" {
            nativeBuildInputs = [ pkgs.nix ];
            modulePath = ./nix/module.nix;
            NIX_PATH = "nixpkgs=${pkgs.path}";
          } ''
            nix-instantiate --eval --strict \
              -E "let
                  module = import \"$modulePath\";
                  lib = (import <nixpkgs> { }).lib;
                  evaled = lib.evalModules {
                    modules = [
                      module
                      { services.nixos-deploy-tool.enable = true; }
                    ];
                  };
                  cfg = evaled.config.services.nixos-deploy-tool.settings;
                  json = builtins.fromJSON (builtins.toJSON cfg);
                in builtins.typeOf json.logLevel" > "$out" 2>&1
            grep -q "string" "$out" || {
              echo "FAIL: logLevel type is not string"
              exit 1
            }
          '';

          hm-module-eval = pkgs.runCommand "hm-module-eval" {
            nativeBuildInputs = [ pkgs.nix ];
            hmModulePath = ./nix/home-module.nix;
            NIX_PATH = "nixpkgs=${pkgs.path}";
          } ''
            nix-instantiate --eval --strict \
              -E "let
                  module = import \"$hmModulePath\";
                  lib = (import <nixpkgs> { }).lib;
                  evaled = lib.evalModules {
                    modules = [
                      module
                      { programs.nixos-deploy-tool.enable = true; }
                    ];
                  };
                  pkg = evaled.config.programs.nixos-deploy-tool.package;
                in builtins.typeOf pkg" > "$out" 2>&1
            grep -q "package" "$out" || {
              echo "FAIL: HM module did not produce a package attribute"
              exit 1
            }
          '';

          service-integrity = pkgs.runCommand "service-integrity" {
            nativeBuildInputs = [ pkgs.nix pkgs.jq ];
            modulePath = ./nix/module.nix;
            NIX_PATH = "nixpkgs=${pkgs.path}";
          } ''
            nix-instantiate --eval --strict --json \
              -E "let
                  module = import \"$modulePath\";
                  lib = (import <nixpkgs> { }).lib;
                  evaled = lib.evalModules {
                    modules = [
                      module
                      { services.nixos-deploy-tool.enable = true; }
                    ];
                  };
                  svc = evaled.config.systemd.services.nixos-deploy-tool;
                in {
                  serviceConfig = svc.serviceConfig;
                  environment  = svc.environment or {};
                  restartTriggers = svc.restartTriggers or [];
                }" > "$out" 2>&1

            jq -e '.serviceConfig | has("Environment") | not' < "$out" > /dev/null || {
              echo "FAIL: Environment found inside serviceConfig"
              exit 1
            }
            jq -e '.serviceConfig | has("RestartTriggers") | not' < "$out" > /dev/null || {
              echo "FAIL: RestartTriggers found inside serviceConfig"
              exit 1
            }
            echo "Service integrity checks passed"
          '';
        }
      );

      vmTests = import ./nix/vm-tests.nix { inherit self nixpkgs; system = "x86_64-linux"; };
    };
}
