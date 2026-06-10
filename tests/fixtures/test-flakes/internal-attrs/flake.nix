{
  description = "Flake with underscore-prefixed internal attrs (like disko module injects)";
  outputs = { self }: {
    nixosConfigurations."test-host" = {
      config = {
        disko.devices = {
          disk = {
            main = {
              type = "disk";
              device = "/dev/sda";
              _packages = "should be stripped";
              _config = "should be stripped";
              content = {
                type = "gpt";
                _meta = "should be stripped";
                partitions = [
                  {
                    name = "root";
                    content = {
                      type = "filesystem";
                      format = "ext4";
                      mountpoint = "/";
                    };
                  }
                  {
                    name = "swap";
                    _hidden = true;
                    content = {
                      type = "swap";
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
