<task>
User request:

{{ prompt }}

Edit `main.py` in the run workspace and build the requested object. Meet the four
quality requirements from the system prompt. Use realistic geometry, model the
primary mechanism, support every part, and avoid unintended overlap.

Start with the preloaded SDK quickstart. Use `read` for only the SDK references,
build123d pages, mesh helper pages, and local examples that answer a current
design question. Then implement the object with
`Part.add(shape, name=..., color=...)`, add prompt-specific checks, and run
`compile`.

Treat every compile signal as design evidence. Preserve prompt-critical visible
geometry while you repair named defects. Finish only after the current workspace
has a successful compile, then return a short visible summary of the object and
its main motion.
</task>
