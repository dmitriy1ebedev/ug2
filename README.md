# UG2 — browser runtime for Linux and Windows

UG2 is a project for a portable, local browser-based game runtime targeting Astra Linux and Windows. The launcher and application are intended to be updated separately from user-supplied game data and saves. No Wine is required by the intended browser runtime architecture.

## Upstream and references

- [th0mk/nfsu2-web](https://github.com/th0mk/nfsu2-web) — primary upstream for the WASM loader, GameSession, WebGPU, audio and input integration. Development references commit `b60e876aef09e7328ecff5a85a97bf2ad834b67f` (MIT). Applicable upstream copyright and license notices will accompany the imported source.
- [WebAssembly/wasi-sdk](https://github.com/WebAssembly/wasi-sdk) — build toolchain dependency (SDK 34), not a source of game logic.

## Distribution and status

This is the public source repository, currently being prepared for the initial source-only publication. Original game assets, executable binaries, game-derived WASM, saves and private development history are not included. Users must supply their own game data. UG2 is an independent project and is not an official game release.

Physical gameplay acceptance on Astra Linux and Windows, and frame-pacing verification on target GPUs, are still pending. Source-only checks do not establish playable-game compatibility.
