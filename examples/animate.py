import math, sys
import numpy as np
from mini_articraft.recon import Rig
from mini_articraft.recon import mesh as M
from mini_articraft.recon import probe
name = sys.argv[1]
m = M.largest_component(M.load_mesh(f"data/meshes/{name}.glb", normalize=True))
a, b = M.segment_two_slabs(m)
base, moving = (a, b) if a.centroid[2] < b.centroid[2] else (b, a)
h = M.hinge_from_contact(moving, base)
rig = Rig(name=name)
rig.add_part("base", base, color=(0.35, 0.37, 0.42))
rig.add_part("lid", moving, color=(0.78, 0.62, 0.42))
lo = math.radians(-95) if name == "laptop" else 0.0
up = 0.0 if name == "laptop" else math.radians(100)
rig.add_joint("hinge", "revolute", "base", "lid", origin=h["origin"], axis=h["axis"], lower=lo, upper=up)
probe.animate_gif(rig, "hinge", f"data/agent_runs/{name}/anim.gif", n=22)
print(f"wrote data/agent_runs/{name}/anim.gif")
