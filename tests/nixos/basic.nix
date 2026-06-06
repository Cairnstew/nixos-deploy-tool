{ lib, ... }: {
  name = "nixos-deploy-tool-basic";

  nodes.machine = { ... }: {
    imports = [
      (builtins.getFlake (toString ./../..)).nixosModules.default
    ];
    services.nixos-deploy-tool.enable = true;
  };

  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.succeed("test -f /etc/nixos-deploy/config.json")
    machine.succeed("nixos-deploy --help")
  '';
}
