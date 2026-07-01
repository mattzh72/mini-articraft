<task>
User request:

{{ prompt }}

Create `main.py` in the run workspace. Build a realistic object that satisfies the
request, with recognizable geometry, believable construction details, realistic
proportions, and the main expected articulation.

Use build123d for geometry and the mini-articraft SDK for object structure, joints,
and tests. Add prompt-specific checks with `TestContext`, then run `compile` before
the final response.

Before writing code, use `read` to study the SDK docs, the build123d pages, and
local examples or snippets that relate to this object. Read thoroughly before
you choose the modeling approach and create `main.py`.
</task>
