{ config, lib, pkgs, ... }:

let
  cfg = config.programs.nixos-deploy-tool;
in

{

  options.programs.nixos-deploy-tool = {
    enable = lib.mkEnableOption "nixos-deploy-tool home-manager integration";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.nixos-deploy-tool;
      defaultText = lib.literalExpression "pkgs.nixos-deploy-tool";
      description = "Package to add to the user session";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ];
  };

}
