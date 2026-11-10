# Third-party software and corresponding source

The installer includes selected files from the pinned [Proton-ZLUDA release](https://github.com/chkuendig/Proton-ZLUDA/releases/tag/proton-zluda-11.0-20261108-799caed8). The installer archive carries third-party notices under `licenses/`.

## Corresponding source archive

The source archive accompanying the installer contains the following inputs for its LGPL components.

| Component | Source in the archive | License |
| --- | --- | --- |
| Wine `ntdll.so` | `wine-e60892c.tar.gz` and the Wine patch and build files in `proton-zluda-799caed8.tar.gz` | LGPL-2.1-or-later |
| `libnuma.so.1` | `numactl-2.0.18.tar.gz` and the numactl build commands in `proton-zluda-799caed8.tar.gz` | LGPL-2.1 |

The Proton-ZLUDA source archive contains the build recipe in `.github/workflows/zluda.yml` and `make/`. The Wine submodule is pinned to [ValveSoftware/wine e60892c](https://github.com/ValveSoftware/wine/tree/e60892cc2398b0a83c332a2078c7b85e47bdb42b), with the changes in `patches/wine/`. The numactl input is the [2.0.18 release source](https://github.com/numactl/numactl/releases/tag/v2.0.18) pinned by `make/zluda-deps.json`.

## Other components

- The CUDA implementation comes from [ZLUDA 39ef5ce](https://github.com/chkuendig/ZLUDA/tree/39ef5ce92bb7c2363ba756b3316b8cfce65d5b65) and [zluda-wine bf80022](https://github.com/chkuendig/zluda-wine/tree/bf80022f07cf66fbec96445cf77c12d2081c32ee). Their notices accompany those of the Rust dependencies, LLVM, LLD, and HiGHS used by Proton-ZLUDA.
- The NVAPI implementation comes from [DXVK-NVAPI f9fdf26](https://github.com/jp7677/dxvk-nvapi/tree/f9fdf268e888d17ae9875a4f01908164ff05f740) with the patches in the [Proton-ZLUDA source tree](https://github.com/chkuendig/Proton-ZLUDA/tree/799caed86a971786a0697e7dbe2b35e2df37d171/patches/dxvk-nvapi). The DXVK-NVAPI and NVIDIA NVAPI notices are included.
- The AMD runtime files come from the [ROCm 7.2.4 packages](https://github.com/chkuendig/Proton-ZLUDA/blob/799caed86a971786a0697e7dbe2b35e2df37d171/make/zluda-deps.json) pinned in the build recipe. The component notices are included.

The game and the NVIDIA PhysX System Software are governed by their respective terms. The installer finds or obtains PhysX separately on the user's device.
