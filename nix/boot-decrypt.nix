{ name, ageSource, targetPath, decryptKey }:

{ config, lib, pkgs, ... }:

let
  serviceName = "agenix-boot-decrypt-${name}";
in

{
  systemd.services.${serviceName} = {
    description = "Boot-time age decryption for ${name}";
    wantedBy = [ "multi-user.target" ];
    before = [ "tailscaled.service" ];
    requires = [ "tmpfs-keys.mount" ];

    unitConfig = {
      DefaultDependencies = false;
    };

    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${pkgs.age}/bin/age -d -i ${decryptKey} -o ${targetPath} ${ageSource}";
      RemainAfterExit = true;
    };
  };
}
