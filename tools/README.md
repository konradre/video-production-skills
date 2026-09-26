# tools — the two host-side instruments the finish skills call

Both run against a Windows workstation that holds the licensed software (Topaz Video, DaVinci Resolve
Studio + the Dehancer OFX plugin); the pipeline itself lives on the Linux side (WSL2 in our case) and hands
clips across a shared path. `look-library/GUIDE.md` §5 covers the topology, the installs and the bridge.

## topaz-upscale/topaz_upscale.py — the local reconstructive upscale

Drives the bundled ffmpeg (`tvai_up`) of [Topaz Video](https://www.topazlabs.com/topaz-video), called Topaz Video AI
before the rename, from WSL. Log in to Topaz once in its GUI (the models download on first use).
`video-finish-qc/scripts/upscale_local.sh` wraps it.

The wrapper looks for the renamed app first and the old one second. The renamed app keeps its models in
`C:\ProgramData\Topaz Labs LLC\Topaz Video\models\models` (Topaz's troubleshooting page); Topaz Video AI used the
same places with `Topaz Video AI` in the path. We measured the wrapper on Topaz Video AI 6.0.2 only. Topaz has said it
will phase out its command line, and the wrapper runs the ffmpeg that command line uses, so check it on a new release
before a job depends on it.

```bash
python3 tools/topaz-upscale/topaz_upscale.py --in takes/A.mp4 --model rhea-1 --scale 4 --out-dir "C:\renders"
```

| env | default | meaning |
|---|---|---|
| `TOPAZ_FFMPEG` | detected: `/mnt/c/Program Files/Topaz Labs LLC/Topaz Video/ffmpeg.exe`, else the same path under `Topaz Video AI` | Topaz's ffmpeg |
| `TVAI_MODEL_DIR` · `TVAI_MODEL_DATA_DIR` | detected: the first folder that holds models, `C:\ProgramData\Topaz Labs LLC\Topaz Video\models\models` or `…\Topaz Video\models`, else `…\Topaz Video AI\models` and `…\Topaz Video AI` | passed through WSLENV |
| `TOPAZ_OUT_DIR` | `renders` | a Windows-reachable output directory; a C: path renders fastest |
| `TOPAZ_UPSCALE_PY` | this file, resolved from the skill's real path | what `upscale_local.sh` calls |

## resolve-pass/resolve_pass.py — the unattended hero pass

Per clip: import → its own timeline → `ApplyGradeFromDRX(<look>.drx)` → a 10-bit mezzanine render → JSON.
Runs under the **Windows** Python that can import `DaVinciResolveScript` (a venv beside the bridge repo works).
`video-finish-qc/scripts/hero_pass.sh` wraps it. Install the in-app bridge from
[samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) once; every session the
human launches Resolve and opens a project. `--transport auto` tries Local external scripting (Studio) first and
falls through to the bridge, so starting `Workspace ▸ Scripts ▸ resolve_bridge` is needed only when Local refuses —
check the bridge's port (49632) and a scripting probe before asking anyone to start either.

```bash
<windows venv python> tools/resolve-pass/resolve_pass.py --look ads-clean --in "C:\renders\A__rhea-1x4.mp4" \
    --out-dir "C:\hero-pass\renders" --format mov --codec DNxHR_HQX --transport auto --wait 60
<windows venv python> tools/resolve-pass/resolve_pass.py --list-codecs      # what this install offers, BY EXTENSION
```

| env | default | meaning |
|---|---|---|
| `RESOLVE_PY` | — | the Windows venv interpreter (`hero_pass.sh --python`) |
| `RESOLVE_PASS_DIR` | `tools/resolve-pass`, resolved from the skill's real path | what `hero_pass.sh` runs |
| `RESOLVE_PASS_OUT` | `C:\hero-pass\renders` | render directory |
| `RESOLVE_PASS_PROJECT` | `hero-pass` | the Resolve project the pass opens or creates |
| `LOOK_LIBRARY_DRX` | `look-library/drx` | the authored `.drx` grades |
| `DAVINCI_RESOLVE_MCP_DIR` | `C:\tools\davinci-resolve-mcp` | the bridge repository (its `src/utils/resolve_bridge_client.py`) |
| `RESOLVE_SCRIPT_HOST` · `RESOLVE_SCRIPT_TIMEOUT` | — | external scripting over the network (Studio) |
| `RESOLVE_PASS_DISTRO` | `Ubuntu` | the WSL distro name for `\\wsl.localhost\` path translation |

Smokes: `smoke_apply_drx_render.py <look.drx>` applies one grade to the open timeline and renders;
`smoke_batch_looks.py` does every look in `look-library/drx/`. Both print a sentinel (`SMOKE-OK`, `BATCH-OK`).
