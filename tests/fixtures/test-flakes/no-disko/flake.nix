{
  description = "Flake with a NixOS host that has no disko.devices";
  outputs = { self }: {
    nixosConfigurations."no-disko-host" = {
      config = {
        boot.loader.grub.enable = true;
      };
    };
  };
}
