{ stdenv, python3Packages, fetchPypi, fetchFromGitHub, pkgs, runtimeShell }:
let
  latestCython0 = python3Packages.cython_0.overrideAttrs (self: super: rec {
    version = "0.29.37";
    src = fetchPypi {
      pname = "Cython";
      inherit version;
      hash = "sha256-+BPUpt2Ure5dT/JmGR0dlb9tQWSk+sxTVCLAIbJQTPs=";
    };
  });
  imgui = { python3Packages, pkg-config, imgui, fetchPypi, fetchFromGitHub }:
    with python3Packages;
    buildPythonPackage rec {
      pname = "imgui";
      version = "2.0.0";

      nativeBuildInputs = [ latestCython0 setuptools ];

      dependencies = [ pyopengl glfw pysdl2 ];

      src = fetchPypi {
        inherit pname version;
        sha256 = "sha256-L7247tO429fqmK+eTBxlgrC8TalColjeFjM9jGU9Z+E=";
      };

      doCheck = false;
    };
  # moderngl-window with applied fix
  moderngl-window = python3Packages.moderngl-window.overrideAttrs
    (self: super: {
      src = fetchFromGitHub {
        owner = "implr";
        repo = "moderngl-window";
        rev = "d089e9b1499449f59d0b138e8501cbeae50844bd";
        hash = "sha256-d+1Q+D4RKIHxToAi+d8q8G43kSCTRVt0PsKMk+WECCQ=";
      };
    });
  pythonEnv = pkgs.python3.withPackages (p:
    with p; [
      pip
      moderngl
      moderngl-window
      pillow
      numpy
      xxhash
      dill
      pylint
      pyrr
      (pkgs.callPackage imgui { })
    ]);
in
stdenv.mkDerivation {
  name = "game";
  src = ./.;

  buildInputs = [ pythonEnv ];
  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    mkdir -p $out/libexec $out/bin
    cp -r . $out/libexec

    makeWrapper \
      "''${out}/libexec/server.py" $out/bin/server \
      --set PYTHONHOME "${pythonEnv}"

    makeWrapper \
      "''${out}/libexec/client.py" $out/bin/client \
      --set PYTHONHOME "${pythonEnv}"
  '';

  doConfigure = false;
  doCheck = false;
  allowImportFromDerivation = true;
}
