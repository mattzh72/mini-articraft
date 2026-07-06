# recon SDK — articulate a static mesh in code

You write Python against `mini_articraft.recon`. Load a mesh, split it into
parts, build a `Rig` with joints, verify with collision sweeps, render what you
did, export USD. Save images to `out/` — the harness shows you every image your
script writes, plus stdout.

```python
from mini_articraft.recon import mesh as M, render as R, segment as S
from mini_articraft.recon import probe as P, verify as V
from mini_articraft.recon.rig import Rig
from mini_articraft.recon.usd import write_usd
```

## See the object
- `m = M.load_mesh(path, normalize=True, y_up_to_z_up=False)` — whole mesh (never
  drop components by size; a knob out-tessellates a cabinet).
- `R.render_views([(m, (r,g,b)), ...], "out/x.png", n=4)` — orbit montage.
- `R.look(m_or_parts, "out/v.png", direction=(0,-1,0.3), center=None, zoom=1)`
  — YOUR eyes: render any angle/close-up. Pass a patch centroid as center and
  zoom=2-3 to inspect a region (a seam, a suspect group boundary) up close.
- `R.collage([paths...], "out/sheet.png", cols=3, labels=[...])` — tile images
  into one sheet, if a side-by-side comparison helps you.
- `R.render_grid(m, "out/grid.png")` — grey mesh in a MEASURED coordinate cage
  (bounding box + ticks/labels every 0.1 on x/y/z). Read true extents and
  specify cut planes in REAL coordinates. Use this to place a seam the geometry
  lost: the reference PHOTO tells you the proportion ("lid = top quarter"), the
  grid tells you that is z=+0.12.
- `labels, info = S.cut_at_marks(m, cam, pixels, normal)` — mark the seam line
  in a rendered view (pixels along it); ray-casts to the surface and cuts with
  a plane of that `normal` through the seam. For seams VISIBLE but not creased.
  Simpler when you know the height: `labels = (m.triangles_center[:,2] > z).astype(int)`.
- `labels, k = S.overseg_auto(m)` — face labels for k patches. Components = the
  modeler's parts; one fused blob (scan) gets subdivided geometrically.
- `labels, k = S.reduce_patches(m, labels, k)` — fold decorative clutter into
  ~18 CANDIDATE patches. Always run when k > 20.
- `R.render_numbered(m, labels, k, "out/patches.png")` — ids drawn on patches.
- `R.render_legend(m, labels, k, "out/legend.png")` — one tile per patch,
  isolated in red. READ THIS to identify patches; ids on busy renders mislead.
- `S.sibling_hints(m, labels, k)` — groups of same-size patches (drawers in a
  row, door pairs). Siblings almost always share joint type and axis direction.
- `S.patch_adjacency(m, labels)` — which patches touch which.

## Work in the FIELD, not the triangles (SDF / volumetric)
The scan is a million faces of a smooth field. For reconstruction/refinement and
clean cuts, convert to a signed-distance field and reason with MATH — booleans
are one-liners and always watertight; you can regularize a bad reconstruction.
```python
from mini_articraft.recon import volume as V
sdf = V.mesh_to_sdf(m, res=96)     # solid field (voxelize+fill; handles shells)
lid  = sdf & V.above(sdf, axis=2, value=0.12)   # intersect: the part above z=0.12
base = sdf - V.above(sdf, axis=2, value=0.12)   # difference
square = sdf & V.box(sdf, center, half)         # de-barrel: intersect with a box
part_mesh = lid.to_mesh()          # marching cubes back to triangles (compact)
```
Operators: `a & b` intersect, `a | b` union, `a - b` carve. `V.above/below(sdf,
axis,value)` = half-space; `V.box(sdf,center,half)` = box primitive on the same
grid. Use this when the mesh is a degraded blob (barrel, smoothed seam) — fix the
shape in the field, then `.to_mesh()` each part for the rig.

## Carve parts — labels are YOURS to write
Segmentation is nothing but an int-per-face array. `overseg_auto` gives you a
starting one, but you can construct or edit labels directly with any mask you
can compute:
```python
labels = np.zeros(len(m.faces), int)          # start from scratch if you want
C, N = m.triangles_center, m.face_normals
labels[(C[:, 2] > 0.1) & (N[:, 1] < -0.5)] = 1   # e.g. upper front-facing faces
```
Any per-face logic works: position, normal, probe results, distances to a
seam you found. There is no special cutting tool — a "cut" is just you
assigning different labels to two sets of faces.
- `cr = S.crease_lines(m)` — the SEAM MENU: joints live on creases, and this
  enumerates them as named candidates C0, C1, ... (each: 3D polyline segments,
  `fold_deg`, `length`, `dir`, `mid`), longest first. Print the table, then
  `R.render_creases(m, cr, "out/creases.png")` to see the same ids drawn on
  the object (occlusion-honest). Decide semantically which crease is the joint
  ("the door outline is C2; hinge along its bottom edge") and use that entry's
  geometry in code — no freehand coordinates.
- `v = S.spectral_order(m)` — canonical 1D ordering of the surface (per-face,
  0..1): adjacent faces get nearby values, and the value changes fastest at
  BOTTLENECKS (hinge fillets, pivots, lid seams). On fused scans this is the
  fastest route to the seam: `ts, narrow = S.neck_profile(m, v)`; cut at a
  valley: `labels = (v > ts[narrow.argmin()]).astype(int)`. Works best on
  chain-like objects (clamshells, two-arm tools); many-part furniture needs
  your judgment on top.
- `S.patch_mesh(m, labels, [ids])` — submesh of any label group.
- `clean, strays = S.strip_strays(part_mesh)` — split off rod-like fragments
  that don't belong to a part's bulk (put strays on the parent part).
- `P.probe_from_pixel(m, cam, px, py)` — 3D surface point under a pixel of a
  rendered view, if you want to turn something you SEE into a coordinate.

## Measure (exact answers — prefer these over squinting at renders)
- `sec = M.section(m, point, normal)` — slice with a plane -> 2D profile:
  `sec["loops"]` (closed polylines) + `sec["areas"]`. Nested loops = cavities;
  loop spacing = wall thickness. `R.render_section(sec, "out/sec.png")` draws it.
- `M.ray_probe(m, origin, direction)` -> sorted hit distances along a ray.
  Two close hits = thin panel; big gap after = hollow behind it; use to check
  "is there a real drawer box behind this front, or just a facade?"

## Rebuild in code (route B: measure the mesh, CONSTRUCT the object)
Instead of segmenting scan geometry, rebuild the object from clean solids and
fit it to the target by measuring. Parts get REAL interiors (drawer boxes,
walls) that scans never have.
- `from mini_articraft.recon import build as B, compare as C`
- `B.box(dims, center)`, `B.cylinder(radius, height, center, axis=(0,0,1))`
- `B.open_box(dims, wall, center, open_face="+y")` — 5-slab open box:
  drawer box (open "+z") or cabinet shell (open "+y" = front). Watertight.
- `B.merge(m1, m2, ...)` — weld solids into one rigid part.
- `r = C.compare(built_mesh, target_mesh, out_prefix="out/fit")` — the error
  signal: `r["bbox_err"]` per axis, `r["iou"]` silhouette overlap per view
  (aim > 0.9), overlay images (red=built-only, blue=target-only, dark=match)
  and section-profile overlays. Merge all built parts for the compare.
Fit loop: measure -> build -> compare -> adjust dims/positions -> repeat.
Then rig the CONSTRUCTED parts (joints on clean boxes are trivial) and export.

MESH + GENERATED FUSION (the normal mode): carved mesh pieces stay the visible
object; code only adds what the scan can't see. A facade drawer front becomes
`B.merge(front_mesh, B.box_behind(front_mesh, depth, inward=(0,1,0)))` —
depth from M.ray_probe. Then verify the outside didn't change:
`C.silhouette_check(augmented_whole, original_mesh)["ok"]` must be True.

## Rig + joints
- `rig = Rig(name)`; `rig.add_part(name, mesh, mass=1.0, friction=0.5, color=(r,g,b))`
- `rig.add_joint(name, "revolute"|"prismatic", parent, child, origin=(x,y,z),
  axis=(x,y,z), lower=0.0, upper=1.4)` — revolute limits in radians.
- Compute geometry, don't guess numbers (EXACT signatures — do not invent kwargs):
  - prismatic: `ax, counts, scores = V.best_slide_axis(moving_mesh, list_of_other_meshes)`
    — ranks all 6 directions by collision decay. Trust it over intuition.
  - revolute: `h = V.best_hinge(moving_mesh, list_of_other_meshes)` ->
    `h["axis"], h["origin"], h["score"]` — sweeps all 12 bbox-edge hinge lines
    (both signs), returns the one that swings cleanest. USE THIS for doors/lids.
    (`M.hinge_from_contact(moving, body)` is a fallback for parts joined along
    one seam like scissors; it FAILS on flush doors framed on all sides.)
  - `V.sweep_joint(rig, joint_name, steps=5) -> list[int]` — contact counts for
    one existing joint of a built rig. Takes a Rig, NOT meshes.
  - joint LIMITS are computed, never guessed:
    `upper = V.slide_limit(moving, others, axis)` (prismatic travel);
    `upper = V.swing_limit(moving, others, axis, origin)` (revolute radians).
  - `S.patch_adjacency(m, labels)` returns `dict[int, set[int]]` keyed by patch
    id (`adj[3]` = set of neighbors; NOT a matrix — no `adj[i, j]`).
  - `V.motion_report(rig)` returns a dict {joint: {"contacts_closed_to_open":
    [...], "verdict": "clean|grinding|BLOCKED"}} — index it, don't string-search.

## Verify (do this before you finish)
- `V.motion_report(rig)` — per joint: contact counts closed->open + verdict
  `clean` (decays to ~0, correct) / `grinding` / `BLOCKED` (bad group or axis).
  Print it. Never finish with a BLOCKED joint.
- `P.render_open(rig, joint_name, "out/open.png", states=3, azim=deg)` — motion
  montage; set azim so the camera faces the direction the part moves.
- `P.render_rig(rig, "out/rig.png")` — all parts colored, closed state.

## Export
- `write_usd(rig, "out/object.usda")` — physics USD (rigid bodies, colliders,
  friction, joint limits).

## What counts as a moving part
Joints belong to the object's STRUCTURE: doors, drawers, lids, blades, knobs.
Loose contents sitting on/in the object (books, dishes, props) are NOT joints —
a clean collision sweep does not make a book a drawer. Leave decorative
contents in the base.

## Method that works
1. overseg + legend, identify patches; 2. group patches into parts (every patch
belongs somewhere; a patch touching only door patches IS door — handles must
move with their door); 3. physics for axes; 4. motion_report + open renders;
5. fix anything not `clean`, then export.
