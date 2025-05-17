
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.python310Packages.pip
    pkgs.python310Packages.python-dotenv
    pkgs.python310Packages.gradio
  ];
}
