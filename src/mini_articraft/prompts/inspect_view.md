You also have an `inspect_view` tool. A successful compile confirms the model is
connected and valid, but only a rendered image shows the visual quality the checks
cannot judge: gaps, mounting blocks, seams, whether a handle reads as molded or a
hinge seats. After a successful compile, call `inspect_view` to look at the object
-- orbit with azimuth/elevation, frame a part or shape with `target` and tighten
with `zoom`, isolate parts with `only`, and actuate the main motion with `pose`.
When a compile error names a shape, inspect that shape to see the problem. Fix what
looks wrong and compile again; finish only when the workspace compiles and the
rendered views look right.
