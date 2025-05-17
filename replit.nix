
{ pkgs }: {
  deps = [
    pkgs.python3Full
    pkgs.nodejs
    pkgs.poetry
  ];
  env = {
    PYTHONBIN = "${pkgs.python3Full}/bin/python3";
    LANG = "en_US.UTF-8";
  };
}
