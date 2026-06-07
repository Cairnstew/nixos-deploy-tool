{ lib, ... }: {
  name = "nixos-deploy-tool-basic";

  nodes.machine = { ... }: {
    imports = [
      (builtins.getFlake (toString ./../..)).nixosModules.default
    ];
    services.nixos-deploy-tool.enable = true;
  };

  testScript = ''
    start_all()
    machine.wait_for_unit("multi-user.target")

    machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q 'ExecStart.*nixos-deploy'")
    machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q 'Type=oneshot'")
    machine.succeed("systemctl cat nixos-deploy-tool.service | grep -q -v 'Restart='")

    config = machine.succeed("cat /etc/nixos-deploy/config.json")
    import json
    parsed = json.loads(config)
    assert "logLevel" in parsed
    assert parsed["logLevel"] == "info"

    machine.succeed("nixos-deploy --help")
    machine.succeed("nixos-deploy iso list")
    machine.succeed("nixos-deploy secrets list")
  '';
}
