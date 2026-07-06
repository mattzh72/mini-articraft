"""Download a varied articulable test bed from Objaverse (free, no credits) and
render each so we can develop the general articulation workflow on real meshes."""
import numpy as np, math, trimesh, objaverse
from pathlib import Path
from PIL import Image, ImageDraw
from mini_articraft.recon import mesh as M
from mini_articraft.recon.render import Camera, look_at, rasterize

CATS = ["laptop_computer","microwave_oven","cabinet","drawer","toolbox",
        "suitcase","scissors","book","oven","refrigerator"]
lvis = objaverse.load_lvis_annotations()
picks = {c: lvis[c][0] for c in CATS if c in lvis}  # first UID per category
print("downloading", len(picks), "objects...", flush=True)
objs = objaverse.load_objects(list(picks.values()))  # {uid: glb path}

out = Path("data/testbed"); out.mkdir(parents=True, exist_ok=True)
def shot(m, az, W=220):
    lo,hi=m.bounds; c=(lo+hi)/2; rad=float(np.linalg.norm(hi-lo))*1.4
    e=math.radians(18); a=math.radians(az)
    eye=c+rad*np.array([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)])
    R,t=look_at(eye,c); cam=Camera(W,W,.95*W,.95*W,W/2,W/2,R,t)
    return rasterize([(m,(0.65,0.62,0.68))],cam)
rows=[]
for cat,uid in picks.items():
    p=objs.get(uid)
    if not p: continue
    try:
        m=M.load_mesh(p, normalize=True, y_up_to_z_up=True)
        m.export(str(out/f"{cat}.glb"))
        row=np.concatenate([shot(m,az) for az in (30,120,210)],1)
        im=Image.fromarray(row); ImageDraw.Draw(im).text((4,4),f"{cat} ({len(m.faces)}f)",fill=(200,0,0))
        rows.append(np.asarray(im)); print(f"  {cat}: {len(m.faces)}f", flush=True)
    except Exception as e: print(f"  {cat} FAIL {repr(e)[:80]}", flush=True)
if rows:
    w=max(r.shape[1] for r in rows); rows=[np.pad(r,((0,0),(0,w-r.shape[1]),(0,0)),constant_values=255) for r in rows]
    Image.fromarray(np.concatenate(rows,0)).save("data/testbed/TESTBED.png")
    print("wrote data/testbed/TESTBED.png")
