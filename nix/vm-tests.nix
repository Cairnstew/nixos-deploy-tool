{ self, nixpkgs, system ? "x86_64-linux" }:

let
  pkgs = nixpkgs.legacyPackages.${system};
in

{
  basic = pkgs.testers.runNixOSTest {
    name = "nixos-deploy-tool-basic";
    nodes.machine = { ... }: {
      imports = [ self.nixosModules.default ];
      services.nixos-deploy-tool.enable = true;
    };
    testScript = ''
      machine.wait_for_unit("multi-user.target")
      machine.succeed("test -f /etc/nixos-deploy/config.json")
      machine.succeed("nixos-deploy --help")
    '';
  };
}
