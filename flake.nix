{
  description = "Ax-Shell - A hackable shell for Hyprland, powered by Fabric.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    fabric = {
      url = "github:Fabric-Development/fabric";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    fabric-gray = {
      url = "github:Fabric-Development/gray";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      home-manager,
      fabric,
      fabric-gray,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      with pkgs;
      {
        packages = {
          default = self.packages."${system}".ax-shell;
          tabler-icons = pkgs.callPackage ./nix/tabler-icons.nix { };
          ax-shell = pkgs.callPackage ./nix/ax-shell.nix {
            inherit fabric fabric-gray;
            inherit (self.packages."${system}") tabler-icons;
            inherit (pkgs) networkmanager playerctl python3;
            python3Packages = pkgs.python3Packages;
          };
        };
        homeManagerModules = {
          ax-shell = import ./nix/hm-module.nix;
          default = self.homeManagerModules.ax-shell;
        };
      }
    );
}
