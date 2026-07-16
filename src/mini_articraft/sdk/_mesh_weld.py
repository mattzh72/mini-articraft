from __future__ import annotations

import manifold3d
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from trimesh.proximity import signed_distance

from mini_articraft.sdk._mesh_core import MeshGeometry

_MAX_GRID_POINTS = 900_000
_FAR = 1.0e3


def _smax(a: np.ndarray, b: np.ndarray, radius: float) -> np.ndarray:
    """Polynomial smooth maximum: a rounded blend of two distance fields.

    manifold3d's level_set treats the interior as SDF > 0 (positive inside), so a
    union is a max and a *smooth* union is this smooth-max.
    """
    h = np.clip(0.5 + 0.5 * (a - b) / radius, 0.0, 1.0)
    return b * (1.0 - h) + a * h + radius * h * (1.0 - h)


def _mesh_field(mesh, pts: np.ndarray, band: float) -> np.ndarray:
    """Signed distance to `mesh`, POSITIVE inside, exact only near its bounds.

    Points farther than `band` from the mesh bounding box get a large negative
    value; they are outside the blend region and cannot affect the welded surface,
    so skipping the expensive exact query there is safe and much faster.
    """
    # trimesh signed_distance is already positive inside -- matches manifold's convention.
    sd = np.full(len(pts), -_FAR, dtype=np.float64)
    bmin, bmax = mesh.bounds
    near = np.all((pts >= bmin - band) & (pts <= bmax + band), axis=1)
    if near.any():
        sd[near] = signed_distance(mesh, pts[near])
    return sd


def weld(
    *geometries: MeshGeometry, radius: float = 0.006, voxel: float | None = None
) -> MeshGeometry:
    """Smooth-union overlapping solids into one blended solid (a molded fillet join).

    This is a *smooth union*: it blends the pieces' signed distance fields with a
    smooth-minimum, then re-extracts one surface (marching tetrahedra). Unlike a
    boolean union -- which keeps the exact input surfaces and leaves a SHARP seam --
    this grows a rounded fillet of size `radius` at the junction, like smoothing clay
    over a joint. It is approximate (resampled on a voxel grid), so reach for it only
    when you want a molded look; use `boolean_union`/`boolean_difference` for an exact
    conforming join.

    Use it to mold a protrusion into a form -- a handle into a body, a spout into a
    shell: place the pieces so they overlap (overlap within a part is free), then weld
    them into a single molded shape and add THAT to the part.

    Weld pieces that share a color/material, since the result is one shape. The blend
    only bridges gaps up to about `radius`; pieces farther apart than that stay
    separate, so overlap them first.
    """
    geoms = list(geometries)
    if len(geoms) < 2:
        raise ValueError("weld needs at least two geometries")
    radius = float(radius)
    if radius <= 0.0:
        raise ValueError("radius must be positive")

    meshes = []
    for index, geometry in enumerate(geoms):
        if not isinstance(geometry, MeshGeometry):
            raise TypeError(f"geometries[{index}] must be MeshGeometry")
        geometry.validate()
        if not geometry.is_watertight:
            raise ValueError(f"geometries[{index}] must be a closed manifold solid to weld")
        meshes.append(geometry.to_trimesh())

    mins = np.min([m.bounds[0] for m in meshes], axis=0)
    maxs = np.max([m.bounds[1] for m in meshes], axis=0)
    margin = 4.0 * radius
    lo = np.asarray(mins) - margin
    hi = np.asarray(maxs) + margin

    if voxel is None:
        voxel = radius * 0.6
    voxel = float(voxel)
    if voxel <= 0.0:
        raise ValueError("voxel must be positive")
    dims = np.ceil((hi - lo) / voxel).astype(int) + 1
    while int(np.prod(dims)) > _MAX_GRID_POINTS:
        voxel *= 1.3
        dims = np.ceil((hi - lo) / voxel).astype(int) + 1

    axes = [lo[i] + voxel * np.arange(dims[i]) for i in range(3)]
    grid = np.meshgrid(axes[0], axes[1], axes[2], indexing="ij")
    pts = np.column_stack([g.ravel() for g in grid])

    band = 3.0 * radius + voxel
    field = _mesh_field(meshes[0], pts, band).reshape(dims)
    for mesh in meshes[1:]:
        sd = _mesh_field(mesh, pts, band).reshape(dims)
        field = _smax(field, sd, radius)

    if field.max() < 0.0:
        raise ValueError("weld produced no solid; check that the pieces are valid closed meshes")

    interp = RegularGridInterpolator(
        tuple(axes), field, bounds_error=False, fill_value=float(min(field.min(), -voxel))
    )

    def sdf(x: float, y: float, z: float) -> float:
        return float(interp([[x, y, z]])[0])

    solid = manifold3d.Manifold.level_set(
        sdf, [lo[0], lo[1], lo[2], hi[0], hi[1], hi[2]], voxel, 0.0
    )
    if solid.is_empty():
        raise ValueError(
            "weld produced an empty solid; the pieces are farther apart than `radius` "
            "allows -- overlap them or increase radius"
        )

    mesh = solid.to_mesh()
    verts = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    faces = np.asarray(mesh.tri_verts, dtype=np.int64)
    return MeshGeometry(
        vertices=[(float(v[0]), float(v[1]), float(v[2])) for v in verts],
        faces=[(int(f[0]), int(f[1]), int(f[2])) for f in faces],
    )


__all__ = ["weld"]
