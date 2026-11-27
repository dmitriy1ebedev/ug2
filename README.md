<h1 align="center">UG2</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.a.26-blue" alt="Last internal portable version 0.1.a.26">
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Alpha">
  <img src="https://img.shields.io/badge/python-3.7%2B-3776AB?logo=python" alt="Python 3.7+ target">
  <img src="https://img.shields.io/badge/javascript-ES%20modules-F7DF1E?logo=javascript" alt="JavaScript">
  <img src="https://img.shields.io/badge/runtime-WebAssembly-654FF0?logo=webassembly" alt="WebAssembly target">
  <img src="https://img.shields.io/badge/linux-amd64%20%7C%20arm64-lightgrey?logo=linux" alt="Linux target amd64 and arm64">
  <img src="https://img.shields.io/badge/windows-amd64-lightgrey" alt="Windows x64 target">
  <img src="https://img.shields.io/badge/Astra%20Linux%201.7-target%20%2F%20validation%20pending-yellow" alt="Astra Linux 1.7 target; device validation pending">
  <a href="https://github.com/dmitriy1ebedev/ug2/actions/workflows/ci.yml"><img src="https://github.com/dmitriy1ebedev/ug2/actions/workflows/ci.yml/badge.svg" alt="GitHub CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
</p>

<p align="center"><b>Independent browser compatibility project</b></p>

UG2 develops a portable local browser runtime for Linux and Windows, with an independent Python launcher/server and JavaScript interface. The intended engine uses WebAssembly and WebGPU; Wine is not required by the intended architecture.

**Public snapshot:** independent archive verification code and synthetic regression tests. This is not a playable release. The latest internal portable build is `0.1.a.26`; the public source has its own Git revision and contains neither a compiled game engine nor game assets.

## Features and architecture

- Portable local launcher; separate user data and application updates (development target).
- Local browser execution; WebAssembly, WebGPU and Web Audio (runtime target).
- Data integrity checks with SHA-256, path validation and strict manifest parsing (public code).
- No proprietary inputs or installed game needed to run the public tests.
- No game-specific executable selection, game-derived source or WASM in the public snapshot.

| Component | Technology / target |
| --- | --- |
| Local launcher and server | Python 3.7+ target; public CI Python 3.12 |
| Browser interface | JavaScript ES modules, HTML, CSS |
| Runtime | WebAssembly (wasm32), WebGPU, Web Audio; game-specific build excluded |
| Linux | amd64 / arm64 targets |
| Windows | amd64 target |
| Astra Linux 1.7 | Target; physical device and gameplay acceptance pending |
| Public build output | Source-only snapshot; no native Go binary or game executable |

## Quick start (public source)

Requires Python 3.7+ and Git. Run the synthetic tests:

```sh
git clone https://github.com/dmitriy1ebedev/ug2.git
cd ug2
python3 tools/public_source_gate.py
python3 -m unittest discover -s tests -v
```

Verify a user-provided ZIP conforming to the independent `ug2-user-data/v1` integrity manifest:

```sh
python3 tools/verify_user_archive.py /path/to/data.zip
```

This checks structure and content hashes without extracting or executing files; it does not establish licensing or game compatibility.

## Project status

Alpha. Public development is limited to reviewed independent components; full game-specific runtime publication remains on hold pending rights review. Actual Astra 1.7 and Windows gameplay, GPU performance and frame pacing are not yet accepted. CI uses synthetic data and does not substitute for target-device validation.

## Acknowledgements

- [th0mk/nfsu2-web](https://github.com/th0mk/nfsu2-web), archived MIT revision `b60e876aef09e7328ecff5a85a97bf2ad834b67f`; reference for browser integration.
- Talha Müdürrisoğlu, original recompiler and runtime work; see the [upstream MIT notices](docs/UPSTREAM-LICENSE.txt).
- [WebAssembly/wasi-sdk](https://github.com/WebAssembly/wasi-sdk), toolchain reference.

## License and mirrors

Independently authored public source: [MIT License](LICENSE) (SPDX: MIT). Third-party notices remain applicable. The license grants no rights to the original game, trademarks, assets or derived game code. Users must provide lawfully obtained data. UG2 is not affiliated with Electronic Arts. See [public source boundary](docs/PUBLIC-SCOPE.md).

[GitHub](https://github.com/dmitriy1ebedev/ug2) (primary) · [GitVerse](https://gitverse.ru/dmitriy_1ebedev/ug2) (mirror; synchronization status may differ). Only reviewed public snapshots may be mirrored; the internal development tree is not a public export.
