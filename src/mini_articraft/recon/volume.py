"""Volumetric (SDF) representation — the substrate the neural model actually
used before Marching-Cubes handed us a million-face mesh. Work in the FIELD:
booleans are one-liners (min/max), cuts are half-spaces, geometry is smooth and
compact. Re-extract a mesh only at the end.

    sdf = V.mesh_to_sdf(mesh)          # solid field from a (shell) scan mesh
    lid = sdf & V.above(sdf, z=0.12)   # intersect -> the part above z=0.12
    mesh2 = lid.to_mesh()              # marching cubes back to triangles
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh


@dataclass
class SDF:
    """Signed distance on a regular grid. <0 inside, 0 on surface, >0 outside.
    grid: (nx,ny,nz) float; origin: world coord of grid[0,0,0]; pitch: voxel size."""
    grid: np.ndarray
    origin: np.ndarray
    pitch: float

    # ---- boolean algebra (the whole point) ----
    def __and__(self, o):  # intersection
        return SDF(np.maximum(self.grid, o.grid), self.origin, self.pitch)

    def __or__(self, o):   # union
        return SDF(np.minimum(self.grid, o.grid), self.origin, self.pitch)

    def __sub__(self, o):  # difference (carve o out of self)
        return SDF(np.maximum(self.grid, -o.grid), self.origin, self.pitch)

    def value(self, pts) -> np.ndarray:
        """Trilinear-sample the field at world points (N,3)."""
        p = (np.asarray(pts, float) - self.origin) / self.pitch
        from scipy.ndimage import map_coordinates
        return map_coordinates(self.grid, p.T, order=1, mode="nearest")

    def to_mesh(self) -> trimesh.Trimesh:
        """Marching cubes at the zero level set -> a watertight mesh."""
        from skimage.measure import marching_cubes
        v, f, _, _ = marching_cubes(self.grid, level=0.0)
        v = v * self.pitch + self.origin
        return trimesh.Trimesh(vertices=v, faces=f, process=True)

    @property
    def coords(self):
        """World coords of every voxel center: (nx,ny,nz,3)."""
        ax = [self.origin[i] + self.pitch * np.arange(self.grid.shape[i]) for i in range(3)]
        return np.stack(np.meshgrid(*ax, indexing="ij"), -1)


def mesh_to_sdf(mesh: trimesh.Trimesh, res: int = 96, pad: float = 0.08) -> SDF:
    """Mesh -> solid SDF grid. Voxelize + FILL (scan meshes are shells, so we
    solidify first), then an exact distance transform gives signed distance.
    res = grid cells across the longest axis."""
    from scipy.ndimage import distance_transform_edt
    lo, hi = mesh.bounds
    ext = hi - lo
    pitch = float(ext.max()) / res
    lo = lo - pad * ext.max()
    hi = hi + pad * ext.max()
    dims = np.ceil((hi - lo) / pitch).astype(int)
    vox = mesh.voxelized(pitch=pitch).fill()
    occ = np.zeros(dims, bool)
    ijk = np.floor((vox.points - lo) / pitch).astype(int)
    ok = np.all((ijk >= 0) & (ijk < dims), axis=1)
    occ[tuple(ijk[ok].T)] = True
    # signed distance = dist to nearest surface, negative inside
    din = distance_transform_edt(occ) * pitch
    dout = distance_transform_edt(~occ) * pitch
    sdf = dout - din
    return SDF(sdf.astype(np.float32), lo.astype(np.float32), pitch)


def _prim(sdf: SDF, fn) -> SDF:
    """Build a primitive SDF sampled on the SAME grid as `sdf` (so booleans line up)."""
    return SDF(fn(sdf.coords).astype(np.float32), sdf.origin, sdf.pitch)


def above(sdf: SDF, axis: int = 2, value: float = 0.0) -> SDF:
    """Half-space SDF: negative where coord[axis] > value. Intersect to keep a top."""
    return _prim(sdf, lambda C: value - C[..., axis])


def below(sdf: SDF, axis: int = 2, value: float = 0.0) -> SDF:
    return _prim(sdf, lambda C: C[..., axis] - value)


def box(sdf: SDF, center, half) -> SDF:
    """Box SDF on sdf's grid — for squaring off a barrel: sdf & box(...)."""
    c = np.asarray(center, float); h = np.asarray(half, float)

    def f(C):
        q = np.abs(C - c) - h
        return (np.linalg.norm(np.maximum(q, 0), axis=-1)
                + np.minimum(np.max(q, axis=-1), 0))
    return _prim(sdf, f)
