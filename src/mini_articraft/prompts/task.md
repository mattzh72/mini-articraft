<task>
Create an articulated object for this prompt:

{{ prompt }}

Deliverable:
- Write `main.py` in the run workspace.
- Define `build_object_model()`, `object_model`, and `run_tests()`.
- Define `object_model` as a `mini_articraft.sdk.ArticulatedObject`.
- Declare units on the object, such as `ArticulatedObject("object_name", units="meters")`.
- Use `Frame`, not `Origin`, for joint frames.
- Define `run_tests()` so it returns a `mini_articraft.sdk.TestReport`.
- Include the parts and joints needed for the requested object.
- Use CadQuery for geometry and the mini-articraft SDK for the object and joint structure.
- Use `TestContext` for prompt-specific verification.
- Run `compile` before the final response.
</task>
