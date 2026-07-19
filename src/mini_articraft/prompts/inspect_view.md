You also have an `inspect_view` tool. A successful compile confirms the model is
connected and valid, but only a rendered image shows the visual quality the checks
cannot judge: gaps, mounting blocks, seams, whether a handle reads as molded or a
hinge seats. After a successful compile, call `inspect_view` to look at the object
-- orbit with azimuth/elevation, frame a part or shape with `target` and tighten
with `zoom`, isolate parts with `only`, and actuate the main motion with `pose`.
When a compile error names a shape, inspect that shape to see the problem.

The image carries a 0-1 coordinate grid so a spot you see has an address. When
something looks misplaced -- a gap, a floating piece, a part that grazes instead of
seats -- do not guess coordinates from the picture: pass `probe_px: [u, v]` at that
spot and the result returns the shape it hits and the exact [x, y, z] surface point.
Probe both sides of a bad junction and you have the true positions and the distance
between them; edit with those numbers. Fix what looks wrong and compile again; finish
only when the workspace compiles and the rendered views look right.
