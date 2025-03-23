{
  lib,
  stdenv,
  fetchzip,
}:

stdenv.mkDerivation rec {
  pname = "tabler-icons";
  version = "3.31.0";

  src = fetchzip {
    url = "https://github.com/tabler/tabler-icons/releases/download/v${version}/tabler-icons-${version}.zip";
    sha256 = "sha256-BIOPSrAdKaSaomWsbhPDFzxWlbj7P3rBqGiExaqxdhA=";
    stripRoot = false;
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall

    mkdir -p $out/share/fonts/truetype
    cp webfont/fonts/*.ttf $out/share/fonts/truetype/

    runHook postInstall
  '';

  meta = with lib; {
    description = "Tabler Icons - A set of free MIT-licensed high-quality SVG icons";
    homepage = "https://tabler-icons.io/";
    license = licenses.mit;
    platforms = platforms.all;
  };
}
