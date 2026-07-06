"""Quality-filtered Objaverse test bed: pick clean mid-poly single-object meshes."""
import numpy as np, math, objaverse
from pathlib import Path
from PIL import Image, ImageDraw
from mini_articraft.recon import mesh as M
from mini_articraft.recon.render import Camera, look_at, rasterize

CATS=["cabinet","microwave_oven","drawer","toolbox","suitcase","oven","refrigerator","laptop_computer","briefcase"]
lvis=objaverse.load_lvis_annotations()
# gather candidate uids, load metadata, filter by face count + not animated
cand={c:lvis[c] for c in CATS if c in lvis}
allu=[u for us in cand.values() for u in us]
print("loading annotations for",len(allu),"uids...",flush=True)
ann=objaverse.load_annotations(allu)
def score(u):
    a=ann.get(u,{}); fc=a.get("faceCount",0); an=a.get("animationCount",0)
    if an and an>0: return -1
    if fc<25000 or fc>450000: return -1
    return 1.0/(1+abs(fc-120000)/120000)  # prefer ~120k faces
picks={}
for c,us in cand.items():
    ranked=sorted(us,key=lambda u:-score(u))
    good=[u for u in ranked if score(u)>0][:1]
    if good: picks[c]=good[0]
print("picked",len(picks),"quality meshes; downloading...",flush=True)
objs=objaverse.load_objects(list(picks.values()))
out=Path("data/testbed2"); out.mkdir(parents=True,exist_ok=True)
def shot(m,az,W=220):
    lo,hi=m.bounds;c=(lo+hi)/2;rad=float(np.linalg.norm(hi-lo))*1.4
    e=math.radians(18);a=math.radians(az)
    eye=c+rad*np.array([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)])
    R,t=look_at(eye,c);cam=Camera(W,W,.95*W,.95*W,W/2,W/2,R,t);return rasterize([(m,(0.65,0.62,0.68))],cam)
rows=[]
for c,u in picks.items():
    p=objs.get(u)
    if not p: continue
    try:
        m=M.load_mesh(p,normalize=True,y_up_to_z_up=False)
        m.export(str(out/f"{c}.glb"))
        fc=ann.get(u,{}).get("faceCount","?")
        row=np.concatenate([shot(m,az) for az in (30,120,210)],1)
        im=Image.fromarray(row);ImageDraw.Draw(im).text((4,4),f"{c} ({fc}f orig)",fill=(200,0,0));rows.append(np.asarray(im))
        print(f"  {c}: {fc}f",flush=True)
    except Exception as e: print(f"  {c} FAIL {repr(e)[:70]}",flush=True)
if rows:
    w=max(r.shape[1] for r in rows);rows=[np.pad(r,((0,0),(0,w-r.shape[1]),(0,0)),constant_values=255) for r in rows]
    Image.fromarray(np.concatenate(rows,0)).save("data/testbed2/TESTBED2.png");print("wrote TESTBED2.png",flush=True)
