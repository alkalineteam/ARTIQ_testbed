{
  inputs.extrapkg.url = "git+https://git.m-labs.hk/M-Labs/artiq-extrapkg.git?ref=release-8";
  outputs = { self, extrapkg }:
    let
      pkgs = extrapkg.pkgs;
      artiq = extrapkg.packages.x86_64-linux;
    in {
      # This section defines the new environment
      packages.x86_64-linux.default = pkgs.buildEnv {
        name = "artiq-env";
        paths = [
          # ========================================
          # ADD PACKAGES BELOW
          # ========================================
          (pkgs.python3.withPackages(ps : [
            # List desired Python packages here.
            artiq.artiq
            #ps.paramiko  # needed if and only if flashing boards remotely (artiq_flash -H)
            artiq.flake8-artiq
            artiq.dax
            artiq.dax-applets

            # The NixOS package collection contains many other packages that you may find
            # interesting. Here are some examples:
            ps.pandas
            #ps.numba
            ps.numpy
	          ps.matplotlib
            # or if you need Qt (will recompile):
            #(ps.matplotlib.override { enableQt = true; })
            #ps.bokeh
            #ps.cirq
            #ps.qiskit
            # Note that NixOS also provides packages ps.numpy and ps.scipy, but it is
            # not necessary to explicitly add these, since they are dependencies of
            # ARTIQ and incorporated with an ARTIQ install anyway.
          ]))
          # List desired non-Python packages here
          # Additional NDSPs can be included:
          artiq.korad_ka3005p
          artiq.novatech409b
          # Other potentially interesting non-Python packages from the NixOS package collection:
          pkgs.gtkwave
          pkgs.spyder
          pkgs.R
          pkgs.julia
          # ========================================
          # ADD PACKAGES ABOVE
          # ========================================
        ];
      };
    };
  # This section configures additional settings to be able to use M-Labs binary caches
  nixConfig = {  # work around https://github.com/NixOS/nix/issues/6771
    extra-trusted-public-keys = "nixbld.m-labs.hk-1:5aSRVA5b320xbNvu30tqxVPXpld73bhtOeH6uAjRyHc=";
    extra-substituters = "https://nixbld.m-labs.hk";
  };
}
