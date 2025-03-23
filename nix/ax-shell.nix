{
  lib,
  fabric,
  fabric-gray,
  stdenv,
  networkmanager,
  playerctl,
  tabler-icons,
  python3,
  python3Packages,
  makeWrapper,
}:

let
  # Get the run-widget package from the fabric flake and override it
  run-widget = fabric.packages.${stdenv.system}.run-widget.override {
    extraPythonPackages = with python3Packages; [
      ijson
      pillow
      psutil
      requests
      setproctitle
      toml
      watchdog
    ];
    extraBuildInputs = [
      fabric-gray.packages.${stdenv.system}.default
      networkmanager
      networkmanager.dev
      playerctl
      tabler-icons
    ];
  };

  # Create a Python environment for the 'python' command
  pythonEnv = python3.withPackages (
    ps: with ps; [
      fabric.packages.${stdenv.system}.default
      ijson
      pillow
      psutil
      requests
      setproctitle
      toml
      watchdog
    ]
  );
in

stdenv.mkDerivation rec {
  name = "ax-shell";

  src = ../.;

  nativeBuildInputs = [ makeWrapper ];

  # Include run-widget as a dependency
  buildInputs = [
    run-widget
    pythonEnv
  ];

  dontBuild = true;

  installPhase = ''
    mkdir -p $out/bin
    mkdir -p $out/lib/ax-shell

    # Copy the source files to the output directory
    cp -r . $out/lib/ax-shell/

    # Create a wrapper script that uses run-widget and adds python to PATH
    cat > $out/bin/ax-shell << EOF
    #!/bin/sh
    # Add pythonEnv to PATH so that 'python' command is available
    export PATH="${pythonEnv}/bin:\$PATH"
    # Set PYTHONPATH to include ax-shell directory
    export PYTHONPATH="$out/lib/ax-shell:\$PYTHONPATH"
    # Run the main.py using run-widget
    exec ${run-widget}/bin/run-widget $out/lib/ax-shell/main.py "\$@"
    EOF

    chmod +x $out/bin/ax-shell

    # For debugging: create a simple script to check the environment
    cat > $out/bin/ax-shell-debug << EOF
    #!/bin/sh
    echo "PATH: \$PATH"
    echo "PYTHONPATH: \$PYTHONPATH"
    echo "GI_TYPELIB_PATH: \$GI_TYPELIB_PATH"
    echo "Looking for python:"
    which python || echo "python not found in PATH"
    echo "Python version:"
    python --version || echo "Failed to run python"
    echo "Available in ${pythonEnv}/bin:"
    ls -la ${pythonEnv}/bin
    EOF

    chmod +x $out/bin/ax-shell-debug
  '';

  meta = with lib; {
    description = "A hackable shell for Hyprland, powered by Fabric";
    homepage = "https://github.com/YourUsername/ax-shell"; # Replace with your actual repo
    license = licenses.mit; # Adjust to your license
    platforms = platforms.linux;
  };
}
