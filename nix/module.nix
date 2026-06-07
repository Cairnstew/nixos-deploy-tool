{ config, lib, pkgs, ... }:

let
  cfg = config.services.nixos-deploy-tool;
in

{

  options.services.nixos-deploy-tool = {
    enable = lib.mkEnableOption "nixos-deploy-tool service";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.nixos-deploy-tool;
      defaultText = lib.literalExpression "pkgs.nixos-deploy-tool";
      description = "Package to use as the systemd service binary";
    };

    settings = lib.mkOption {
      type = lib.types.submodule {
        options = {
          flakeRoot = lib.mkOption {
            type = lib.types.str;
            default = "";
            description = "Path to the flake root directory";
          };

          logLevel = lib.mkOption {
            type = lib.types.enum [ "debug" "info" "warn" "error" ];
            default = "info";
            description = "Log verbosity level";
          };

          liveIsoUser = lib.mkOption {
            type = lib.types.str;
            default = "nixos";
            description = "Default SSH user for live ISOs";
          };

          tailscaleOAuth = lib.mkOption {
            type = lib.types.submodule {
              options = {
                clientId = lib.mkOption {
                  type = lib.types.str;
                  default = "";
                  description = "Tailscale OAuth client ID";
                };
                clientSecretFile = lib.mkOption {
                  type = lib.types.str;
                  default = "";
                  description = "Path to Tailscale OAuth client secret file";
                };
              };
            };
            default = { };
            description = "Tailscale OAuth configuration";
          };

          ageBin = lib.mkOption {
            type = lib.types.str;
            default = "${pkgs.age}/bin/age";
            description = "Path to age binary";
          };

          agenixManagerBin = lib.mkOption {
            type = lib.types.str;
            default = "";
            description = "Path to agenix-manager binary (must be set explicitly)";
          };

          nixosAnywhereBin = lib.mkOption {
            type = lib.types.str;
            default = "";
            description = "Path to nixos-anywhere binary (must be set explicitly)";
          };
        };
      };
      default = { };
      description = "Runtime configuration for nixos-deploy-tool";
    };

    environment = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      description = "Environment variables passed to the service";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];
    environment.etc."nixos-deploy/config.json" = {
      text = builtins.toJSON cfg.settings;
      mode = "0444";
    };

    systemd.services.nixos-deploy-tool = {
      description = "nixos-deploy-tool";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];

      environment = cfg.environment;
      restartTriggers = [ config.environment.etc."nixos-deploy/config.json".source ];

      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${cfg.package}/bin/nixos-deploy";
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
      };
    };
  };

}
