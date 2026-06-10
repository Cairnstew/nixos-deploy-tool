{
  description = "Flake with attrset-keyed (GPT-style) disko partitions";
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
                partitions = {
                  root = {
                    size = "50%";
                    content = {
                      type = "filesystem";
                      format = "ext4";
                      mountpoint = "/";
                    };
                  };
                  home = {
                    size = "50%";
                    content = {
                      type = "filesystem";
                      format = "ext4";
                      mountpoint = "/home";
                    };
                  };
                };
              };
            };
          };
        };
      };
    };
  };
}
