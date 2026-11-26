# UG2 — browser runtime for Linux and Windows

UG2 is a project for a portable, local browser-based game runtime targeting Astra Linux and Windows. The launcher and application are intended to be updated separately from user-supplied game data and saves. No Wine is required by the intended browser runtime architecture.

## Upstream and references

- [th0mk/nfsu2-web](https://github.com/th0mk/nfsu2-web) — primary upstream for the WASM loader, GameSession, WebGPU, audio and input integration. Development references commit `b60e876aef09e7328ecff5a85a97bf2ad834b67f` (MIT). Applicable upstream copyright and license notices will accompany the imported source.
- [WebAssembly/wasi-sdk](https://github.com/WebAssembly/wasi-sdk) — build toolchain dependency (SDK 34), not a source of game logic.

## Distribution and status

This is the public source repository, currently receiving its initial source-only publication. Original game assets, executable binaries, game-derived WASM, saves and private development history are not included. Users must supply their own game data. UG2 is an independent project and is not an official game release.

Physical gameplay acceptance on Astra Linux and Windows, and frame-pacing verification on target GPUs, are still pending. Source-only checks do not establish playable-game compatibility.

## Initial source snapshot

The first reviewed subset contains the private data pack installer and its synthetic regression tests, from source revision `e6a9ef3c5092ace5a18cebe3d82e16047ccdf42c`. Only synthetic fixtures are used by CI; the launcher and full source suite are not yet published here. Run `python3 -m unittest discover -s tests -p 'test_install_data_pack.py' -v` locally. This is not a playable release. See [upstream license notice](docs/UPSTREAM-LICENSE.txt).
