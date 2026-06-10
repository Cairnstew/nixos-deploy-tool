{
  description = "Minimal flake with list-style disko partitions";
  outputs = { self }: {
    nixosConfigurations."test-host" = {
      config = {
        disko.devices = {
          disk = {
            main = {
              type = "disk";
              device = "/dev/sda";
              content = {
                type = "gpt";
                partitions = [
                  {
                    name = "root";
                    size = "100%";
                    content = {
                      type = "filesystem";
                      format = "ext4";
                      mountpoint = "/";
                    };
                  }
                ];
              };
            };
          };
        };
      };
    };
  };
}
