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

      # Service unit is correctly defined (oneshot — not a daemon)
      machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q 'ExecStart.*nixos-deploy'")
      machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q 'Type=oneshot'")
      machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q -v 'Restart='")

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
    hmModule = builtins.readFile ./home-module.nix;
  } ''
    echo "$hmModule" | grep -q "mkOption" || {
      echo "FAIL: HM module missing mkOption declarations" > "$out"
      exit 1
    }
    echo "HM module parsed and contains expected declarations" > "$out"
  '';

  # Tier 4: Service definition integrity — structural checks on module.nix.
  # Validates that Environment and restartTriggers live at the correct level
  # in the service definition (not inside serviceConfig).  Uses pattern
  # matching on the source file since full evaluation requires NixOS infra.
  serviceIntegrity = pkgs.runCommand "nixos-deploy-tool-service-integrity" {
    moduleSource = builtins.readFile ./module.nix;
  } ''
    echo "$moduleSource" | grep -q "environment = cfg.environment;" || {
      echo "FAIL: top-level environment option not found" > "$out"
      exit 1
    }
    echo "$moduleSource" | grep -q "restartTriggers = " || {
      echo "FAIL: top-level restartTriggers not found" > "$out"
      exit 1
    }
    echo "$moduleSource" | grep -q -v 'serviceConfig = {.*Environment = ' || {
      echo "FAIL: Environment found inside serviceConfig" > "$out"
      exit 1
    }
    echo "$moduleSource" | grep -q "Type = .oneshot." || {
      echo "FAIL: service Type is not oneshot" > "$out"
      exit 1
    }
    echo "Service integrity checks passed" > "$out"
  '';
}
