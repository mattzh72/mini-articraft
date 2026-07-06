"""Code-writing articulation agent: ONE tool — run Python against the recon SDK.

The agent writes/rewrites a script each turn; we exec it in a subprocess, return
stdout/stderr and every image it saved under out/. No bespoke tools: probing,
grouping, rigging, verification are all SDK calls the agent composes in code.

Run: .venv/bin/python examples/agent_code.py --model gemini drawer
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(str(ROOT / ".env"))
sys.path.insert(0, str(ROOT / "src"))

from mini_articraft.agent.tools._core import result_item  # noqa: E402

OUT = Path("data/code_runs")
SDK_DOC = (ROOT / "src/mini_articraft/recon/SDK.md").read_text()

SYSTEM = f"""You articulate static 3D meshes into physically-jointed rigs by
WRITING PYTHON against the recon SDK, then looking at the images your code saves.

{SDK_DOC}

Call run(code=...) with a complete script (it fully replaces the previous one).

SEEING IMAGES: renders are written to disk; you only SEE the ones you request
by printing a line `VIEW: out/<file>.png` (max 6 per run). Request only what
you need to decide — numbers you print are usually a sharper signal than
pixels.

Work like an investigator: start with small THROWAWAY probe scripts — measure,
section, ray-probe, print numbers, render one view — to answer specific
questions ("is there a box behind this front?", "which patches touch patch 7?").
Choose your own viewpoints: R.look(...) renders any angle or close-up (aim it
at a patch centroid with zoom=2-3 to inspect seams and group boundaries).
Only when you understand the object, write the full rig script. Probe scripts
are cheap; wrong rigs are expensive.

The working directory PERSISTS between runs: cache expensive results to files
(np.save("out/labels.npy", labels), mesh.export("out/part.ply")) and reload
them in later scripts instead of recomputing.

Finish by writing the USD and replying DONE with a one-line summary of parts +
joints. The mesh path and output dir are given in the task."""

TOOL = {"type": "function", "name": "run",
        "description": "Execute a complete Python script; returns stdout/stderr and all images it saved under out/.",
        "parameters": {"type": "object",
                       "properties": {"code": {"type": "string"}},
                       "required": ["code"], "additionalProperties": False}}


def _img(path: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                        "data": base64.b64encode(path.read_bytes()).decode()}}


def make_model(kind: str):
    if kind == "gemini":
        from mini_articraft.models.gemini import GeminiModel
        return GeminiModel()
    from mini_articraft.models.openai import OpenAIModel
    return OpenAIModel()


def write_trace(workdir: Path, entries: list[dict]) -> None:
    """Linear review page. Every entry appears in exact chronological order,
    each labeled by direction:
      -> MODEL   what the harness sent (task, results, images, interventions)
      <- AGENT   what the model said + the code it submitted
      EXEC       full stdout/stderr/exit of that code
      FILES      everything the script wrote/changed under out/ this turn
    """
    import html as H
    css = """
    body{font-family:-apple-system,sans-serif;max-width:1050px;margin:24px auto;
         color:#1a1a1a;background:#fafafa}
    .step{border:1px solid #ddd;border-radius:8px;margin:14px 0;background:#fff;
          overflow:hidden}
    .hd{padding:6px 12px;font-weight:600;font-size:13px;letter-spacing:.4px}
    .to    .hd{background:#eaf2ff;color:#1a4fa0}
    .frm   .hd{background:#eafbea;color:#1c7a2d}
    .exec  .hd{background:#1b1b1b;color:#eee}
    .files .hd{background:#fff7e0;color:#8a6d00}
    .bd{padding:10px 14px}
    pre{margin:6px 0;padding:10px;border-radius:6px;font-size:12px;
        overflow:auto;max-height:420px;background:#f4f4f4}
    .exec pre{background:#111;color:#d6d6d6}
    .err{color:#ff8484}
    img{max-width:980px;max-height:340px;object-fit:contain;
        border:1px solid #ccc;margin:4px 0}
    details summary{cursor:pointer;font-size:13px;color:#555;margin:4px 0}
    .meta{color:#777;font-size:12px}
    h1{font-size:20px}
    """

    def img_tags(paths):
        return "".join(
            f'<div><img src="{Path(p).resolve().as_uri()}">'
            f'<div class="meta">{H.escape(Path(p).name)}</div></div>'
            for p in paths)

    def step(kind, title, body):
        return f'<div class="step {kind}"><div class="hd">{title}</div><div class="bd">{body}</div></div>'

    rows = []
    for e in entries:
        k = e["kind"]
        if k == "task":
            body = f"<pre>{H.escape(e['text'])}</pre>" + img_tags(e.get("images", []))
            rows.append(step("to", "1 &nbsp;→ MODEL &nbsp;·&nbsp; task + attached images", body))
        elif k == "agent":
            n = e["turn"]
            txt = ""
            if e.get("thinking"):
                txt += (f"<details><summary>model thinking</summary>"
                        f"<pre style='background:#fdf6e3'>{H.escape(e['thinking'])}"
                        f"</pre></details>")
            txt += f"<pre>{H.escape(e['text'])}</pre>" if e.get("text") else \
                   '<div class="meta">(no commentary — straight to code)</div>'
            code = e.get("code")
            codeblk = ""
            if code is not None:
                codeblk = (f"<details open><summary>script submitted "
                           f"({len(code.splitlines())} lines — saved as trace/turn_{n:02d}.py)"
                           f"</summary><pre>{H.escape(code)}</pre></details>")
            rows.append(step("frm", f"{e['seq']} &nbsp;← AGENT &nbsp;·&nbsp; turn {n}", txt + codeblk))
        elif k == "exec":
            out = e.get("stdout") or ""
            err = e.get("stderr") or ""
            body = f"<div class='meta'>exit={e.get('exit')}</div>"
            if out:
                body += f"<pre>{H.escape(out)}</pre>"
            if err:
                body += f"<pre class='err'>{H.escape(err)}</pre>"
            if not out and not err:
                body += "<div class='meta'>(no output)</div>"
            rows.append(step("exec", f"{e['seq']} &nbsp;EXEC &nbsp;·&nbsp; script output", body))
        elif k == "files":
            lst = "".join(f"<li><code>{H.escape(f['name'])}</code> "
                          f"<span class='meta'>{f['size']:,} B {f['tag']}</span></li>"
                          for f in e["files"]) or "<li class='meta'>(none)</li>"
            body = f"<ul>{lst}</ul>" + img_tags(e.get("images", []))
            rows.append(step("files", f"{e['seq']} &nbsp;FILES &nbsp;·&nbsp; written under out/ this turn", body))
        elif k == "feedback":
            body = f"<pre>{H.escape(e['text'])}</pre>"
            if e.get("n_images"):
                body += f"<div class='meta'>+ {e['n_images']} image(s) attached (shown in FILES above)</div>"
            rows.append(step("to", f"{e['seq']} &nbsp;→ MODEL &nbsp;·&nbsp; result fed back", body))
        elif k == "intervention":
            rows.append(step("to", f"{e['seq']} &nbsp;→ MODEL &nbsp;·&nbsp; HARNESS INTERVENTION",
                             f"<pre>{H.escape(e['text'])}</pre>"))
        elif k == "end":
            rows.append(step("frm", f"{e['seq']} &nbsp;■ END &nbsp;·&nbsp; {H.escape(e['text'])}", ""))
    (workdir / "trace.html").write_text(
        f"<html><head><style>{css}</style></head><body><h1>{workdir.name} — run trace"
        f"</h1><div class='meta'>read top to bottom; every block is one message or "
        f"execution in exact order</div>" + "".join(rows) + "</body></html>")


async def run_code(code: str, workdir: Path) -> tuple[dict, list[Path], dict]:
    """Returns (result-for-model, new/changed images, raw trace record).
    ASYNC subprocess: a blocking run would freeze the event loop and starve the
    model websocket's keepalive (observed as 1011 ping timeouts on long meshes).
    The model gets truncated output; the trace keeps everything, including a
    list of ALL files the script wrote or modified under out/."""
    (workdir / "out").mkdir(parents=True, exist_ok=True)
    script = workdir / "script.py"
    script.write_text(code)
    before = {p: p.stat().st_mtime for p in (workdir / "out").glob("**/*") if p.is_file()}
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script), cwd=str(workdir),
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin",
             "OMP_NUM_THREADS": "6", "HOME": str(Path.home())},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        so, se = await asyncio.wait_for(proc.communicate(), timeout=300)
        stdout, stderr = so.decode(errors="replace"), se.decode(errors="replace")
        out = {"stdout": stdout[-4000:], "stderr": stderr[-2500:],
               "exit": proc.returncode}
        raw = {"stdout": stdout, "stderr": stderr, "exit": proc.returncode}
    except asyncio.TimeoutError:
        proc.kill()
        raw = {"exit": -1, "stderr": "TIMEOUT: script exceeded 300s", "stdout": ""}
        return dict(raw), [], {**raw, "files": []}
    changed = []
    for p in sorted((workdir / "out").glob("**/*")):
        if not p.is_file():
            continue
        if p not in before:
            changed.append({"name": str(p.relative_to(workdir)), "size": p.stat().st_size,
                            "tag": "new", "path": p})
        elif p.stat().st_mtime > before[p]:
            changed.append({"name": str(p.relative_to(workdir)), "size": p.stat().st_size,
                            "tag": "modified", "path": p})
    # PULL-based perception: only images the script explicitly names with a
    # "VIEW: <path>" stdout line are sent back to the model. Everything else
    # stays on disk (and in the trace) — the agent chooses its own image diet.
    requested = re.findall(r"^VIEW:\s*(\S+)", raw.get("stdout", ""), re.M)
    imgs = []
    for r in requested:
        p = (workdir / r).resolve()
        if p.suffix == ".png" and p.is_file():
            imgs.append(p)
    raw["files"] = [{k: c[k] for k in ("name", "size", "tag")} for c in changed]
    return out, imgs[:6], raw


async def articulate(name: str, model_kind: str, max_turns: int = 12,
                     task: str | None = None, task_images: list[str] | None = None):
    """task_images: paths attached to the first message (target renders, and —
    for real scans — the original photos; multi-image input is supported)."""
    workdir = (ROOT / OUT / Path(name).stem).resolve()
    # fresh run = fresh outputs: a stale USD from a previous run would satisfy
    # the DONE gate and let the agent quit without building anything
    import shutil
    shutil.rmtree(workdir / "out", ignore_errors=True)
    shutil.rmtree(workdir / "trace", ignore_errors=True)
    (workdir / "trace.html").unlink(missing_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)
    src = name if name.endswith(".glb") else f"data/testbed/{name}.glb"
    mesh_path = (ROOT / src).resolve()
    # reference PHOTO: fine articulation features (seams, flush hinges) are lost
    # in reconstruction but survive in the source image. If a sibling photo
    # exists (same stem .png/.jpg), give it to the agent for identity /
    # proportion / orientation — NOT the geometry, which stays laundered.
    ref_photo = None
    for _ext in (".png", ".jpg", ".jpeg"):
        _cand = mesh_path.with_suffix(_ext)
        if _cand.exists():
            ref_photo = str(_cand); break
    if ref_photo and task_images is None:
        task_images = [ref_photo]
    # LAUNDER the input: flatten to pure geometry (PLY has no scene graph, node
    # names, pivots, or animations) so the agent cannot shortcut articulation
    # by reading authoring metadata from the source file
    from mini_articraft.recon import mesh as _M
    import numpy as _np
    import trimesh as _tm
    _lm = _M.load_mesh(str(mesh_path), normalize=True, y_up_to_z_up=False)
    laundered = workdir / "target.ply"
    # bare vertices+faces only, and SHUFFLED: authoring order puts each part's
    # faces in a contiguous index range (segmentation by array slice), so
    # permute both arrays — geometry/connectivity identical, index order noise
    _rng = _np.random.default_rng(0)
    _vperm = _rng.permutation(len(_lm.vertices))
    _vinv = _np.empty_like(_vperm)
    _vinv[_vperm] = _np.arange(len(_vperm))
    _faces = _vinv[_np.asarray(_lm.faces)]
    _faces = _faces[_rng.permutation(len(_faces))]
    _tm.Trimesh(vertices=_np.asarray(_lm.vertices)[_vperm], faces=_faces,
                process=False).export(str(laundered))
    mesh_path = laundered

    starter = f'''from mini_articraft.recon import mesh as M, render as R, segment as S

m = M.load_mesh("{mesh_path}", normalize=True, y_up_to_z_up=False)
if len(m.faces) > 60000:
    m = R.decimate(m, target=60000)
print("faces:", len(m.faces), "bounds:", m.bounds.round(3).tolist())
print("frame: as-scanned (usually roughly +Z up); the reference photo shows the")
print("true upright orientation — use it to resolve which way is up.")
# MEASURED coordinate cage: read true extents + specify cut planes in real
# coordinates (e.g. "the lid is everything above z=+0.12").
R.render_grid(m, "out/grid.png")
print("VIEW: out/grid.png")
# The object is yours: turn it (R.look), measure it (M.section, M.ray_probe),
# split it. For seams the geometry lost (flush lids/panels), use the reference
# PHOTO for proportion + the grid coords to place a plane cut:
#   labels, info = S.cut_at_marks(m, cam, seam_pixels, normal=(0,0,1))
# or a direct coordinate cut:  labels = (m.triangles_center[:,2] > 0.12).astype(int)
'''
    model = make_model(model_kind)
    photo_note = ("\n\nATTACHED: a reference PHOTO of the real object. The scan LOSES fine "
                  "articulation features (a flush lid seam, a panel line) that are visible "
                  "in the photo. Use the photo to identify the object, its orientation, and "
                  "WHERE its moving parts are PROPORTIONALLY (e.g. 'the lid is the top ~25%'); "
                  "then use the measured grid to place the cut at the real coordinate."
                  if ref_photo else "")
    user_text = task if task is not None else (
        f"Articulate '{Path(name).stem}'. Mesh: {mesh_path}. You have {max_turns} "
        f"run() calls TOTAL; out/{Path(name).stem}.usda must exist by the last one."
        f"{photo_note}\n\nSuggested first call — run this starter to see the measured grid:\n\n"
        f"```python\n{starter}```")
    content = user_text if not task_images else (
        [{"type": "text", "text": user_text}] + [_img(Path(p)) for p in task_images])
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": content}]
    last_stdout = ""
    blocked_bounce = False
    seq = [1]
    trace: list[dict] = [{"kind": "task", "text": user_text,
                          "images": list(task_images or [])}]

    def tpush(kind, **kw):
        seq[0] += 1
        trace.append({"kind": kind, "seq": seq[0], **kw})
        write_trace(workdir, trace)

    for turn in range(1, max_turns + 3):  # +2 grace turns for the BLOCKED gate
        resp = await model.query(messages, tools=[TOOL])
        text, calls = resp["text"], resp["tool_calls"]
        print(f"[{name}/{model_kind}] turn {turn}: {text[:100]}", flush=True)
        messages.append({"role": "assistant", "content": text, "tool_calls": calls})
        if not calls:
            tpush("agent", turn=turn, text=text, code=None,
                  thinking=resp.get("thinking") or "")
            no_usd = not list((workdir / "out").glob("*.usda"))
            # refuse DONE without a USD, or while a joint is BLOCKED
            if no_usd and turn < max_turns:
                msg = ("Not done: no USD exists yet. Keep going — probe "
                       "if you must, but build the rig and write_usd.")
                messages.append({"role": "user", "content": msg})
                tpush("intervention", text=msg)
                continue
            if "BLOCKED" in last_stdout and not blocked_bounce:
                blocked_bounce = True
                msg = ("Not done: your last motion_report shows a BLOCKED joint. "
                       "Fix the group or axis (V.best_hinge / V.best_slide_axis), "
                       "re-verify, AND re-run write_usd before finishing.")
                messages.append({"role": "user", "content": msg})
                tpush("intervention", text=msg)
                continue
            tpush("end", text=f"agent finished after {turn} turns")
            print(f"[{name}] DONE", flush=True)
            break
        for call in calls:
            args = json.loads(call["arguments"] or "{}")
            code = args.get("code", "")
            tpush("agent", turn=turn, text=text, code=code,
                  thinking=resp.get("thinking") or "")
            result, imgs, raw = await run_code(code, workdir)
            last_stdout = (raw.get("stdout") or "") + (raw.get("stderr") or "")
            result["runs_left"] = max_turns - turn
            tdir = workdir / "trace"
            tdir.mkdir(exist_ok=True)
            (tdir / f"turn_{turn:02d}.py").write_text(code)
            frozen = []  # copy: later turns may overwrite out/*.png in place
            import shutil
            for p in imgs:
                dst = tdir / f"turn_{turn:02d}_{Path(p).name}"
                shutil.copyfile(p, dst)
                frozen.append(str(dst))
            tpush("exec", stdout=raw.get("stdout"), stderr=raw.get("stderr"),
                  exit=raw.get("exit"))
            tpush("files", files=raw.get("files", []), images=frozen)
            if max_turns - turn <= 2 and not list((workdir / "out").glob("*.usda")):
                result["WARNING"] = ("almost out of runs and no USD written — "
                                     "your NEXT run must build the best rig you "
                                     "have and write_usd, even if imperfect")
            tail = (result.get("stderr") or result.get("stdout") or "")[-160:].replace("\n", " | ")
            print(f"[{name}]  exit={result.get('exit')} imgs={len(imgs)} :: {tail}", flush=True)
            messages.append(result_item(call["id"], {"result": result}))
            tpush("feedback", text=json.dumps(result, indent=1)[:3000],
                  n_images=len(imgs))
            if imgs:
                messages.append({"role": "user", "content":
                                 [{"type": "text", "text": "Images your script saved:"}]
                                 + [_img(p) for p in imgs]})
    await model.close()


async def main(argv):
    kind = "gemini"
    names = []
    i = 0
    while i < len(argv):
        if argv[i] == "--model":
            kind = argv[i + 1]; i += 2
        else:
            names.append(argv[i]); i += 1
    for n in (names or ["drawer"]):
        await articulate(n, kind)

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
