{ self, nixpkgs, system ? "x86_64-linux" }:

let
  pkgs = nixpkgs.legacyPackages.${system};
in

{
  # Tier 1: Enhanced basic test — service starts, config.json content, CLI subcommands
  basic = pkgs.testers.runNixOSTest {
    name = "nixos-deploy-tool-basic";
    nodes.machine = { ... }: {
      imports = [ self.nixosModules.default ];
      services.nixos-deploy-tool.enable = true;
    };
    testScript = ''
      start_all()
      machine.wait_for_unit("multi-user.target")

      # Service unit exists with correct definition
      machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q 'ExecStart.*nixos-deploy'")

      # Config file exists as valid JSON with expected defaults
      config = machine.succeed("cat /etc/nixos-deploy/config.json")
      import json
      parsed = json.loads(config)
      assert "logLevel" in parsed, f"logLevel missing: {parsed}"
      assert parsed["logLevel"] == "info", f"Expected info, got {parsed['logLevel']}"

      # CLI binary is on PATH and all command groups render help
      machine.succeed("nixos-deploy --help")
      machine.succeed("nixos-deploy iso list")
      machine.succeed("nixos-deploy deploy --help")
      machine.succeed("nixos-deploy tailscale status")
      machine.succeed("nixos-deploy secrets list")

      # CLI exits non-zero on unknown commands
      machine.fail("nixos-deploy nonexistent-command 2>/dev/null")
    '';
  };

  # Tier 2: Settings validation — custom flakeRoot, logLevel, liveIsoUser, env vars
  withSettings = pkgs.testers.runNixOSTest {
    name = "nixos-deploy-tool-with-settings";
    nodes.machine = { ... }: {
      imports = [ self.nixosModules.default ];
      services.nixos-deploy-tool = {
        enable = true;
        settings = {
          flakeRoot = "/custom/flake/path";
          logLevel = "debug";
          liveIsoUser = "admin";
          tailscaleOAuth = {
            clientId = "tskey-client-test";
            clientSecretFile = "/run/secrets/ts-oauth";
          };
        };
        environment = {
          TEST_VAR = "hello-from-env";
          ANOTHER_VAR = "world";
        };
      };
    };
    testScript = ''
      start_all()
      machine.wait_for_unit("multi-user.target")

      # Config file has custom settings
      config = machine.succeed("cat /etc/nixos-deploy/config.json")
      import json
      parsed = json.loads(config)
      assert parsed["flakeRoot"] == "/custom/flake/path", f"flakeRoot: {parsed.get('flakeRoot')}"
      assert parsed["logLevel"] == "debug", f"logLevel: {parsed.get('logLevel')}"
      assert parsed["liveIsoUser"] == "admin", f"liveIsoUser: {parsed.get('liveIsoUser')}"
      assert parsed["tailscaleOAuth"]["clientId"] == "tskey-client-test"

      # Environment variables are attached to the service
      env = machine.succeed("systemctl show nixos-deploy-tool.service -p Environment")
      assert "hello-from-env" in env, f"TEST_VAR missing from Environment: {env}"
      assert "world" in env, f"ANOTHER_VAR missing from Environment: {env}"
    '';
  };

  # Tier 3: Home Manager module evaluation — verifies the HM module evaluates
  # and exposes programs.nixos-deploy-tool.package correctly.
  # Uses nix eval (not a full VM boot) since HM requires separate infrastructure.
  hmModule = pkgs.runCommand "nixos-deploy-tool-hm-module" {
    nativeBuildInputs = [ pkgs.nix ];
    hmModulePath = ./home-module.nix;
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

  # Tier 4: Service definition integrity — verifies serviceConfig structure
  # (service unit format, no stray directives, Environment is not serialised
  # inside serviceConfig, etc.)
  serviceIntegrity = pkgs.runCommand "nixos-deploy-tool-service-integrity" {
    nativeBuildInputs = [ pkgs.nix pkgs.jq ];
    modulePath = ./module.nix;
    NIX_PATH = "nixpkgs=${pkgs.path}";
  } ''
    # Evaluate the module with enable=true, extract the service unit,
    # and verify it using nix-instantiate + jq
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

    # Verify serviceConfig does NOT contain stray directives
    jq -e '.serviceConfig | has("Environment") | not' < "$out" > /dev/null || {
      echo "FAIL: Environment found inside serviceConfig (should be top-level)"
      exit 1
    }
    jq -e '.serviceConfig | has("RestartTriggers") | not' < "$out" > /dev/null || {
      echo "FAIL: RestartTriggers found inside serviceConfig (should be restartTriggers at top level)"
      exit 1
    }
    jq -e '.environment | has("ANOTHER_VAR") | not' < "$out" > /dev/null || {
      echo "FAIL: environment should be empty by default"
      exit 1
    }
    jq -e '.restartTriggers | length == 1' < "$out" > /dev/null || {
      echo "FAIL: expected exactly one restartTrigger"
      exit 1
    }
    echo "Service integrity checks passed" > "$out"
  '';
}
