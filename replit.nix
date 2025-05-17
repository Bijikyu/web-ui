
{ pkgs }: {
  deps = [
    pkgs.python39
    pkgs.python39Packages.pip
    pkgs.python39Packages.python-dotenv
    pkgs.python39Packages.gradio
    pkgs.python39Packages.setuptools
    pkgs.python39Packages.wheel
  ];
}
