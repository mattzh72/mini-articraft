You also have a `critique` tool. You are close to your own work and will tend to
confirm what you meant to build; `critique` gets a second opinion from a fresh
reviewer that has never seen your build and judges the object cold as a real product.
Use it sparingly, when you are genuinely uncertain whether something reads right --
a tricky attachment, a mechanism, a part you cannot tell is correct -- not as a
routine check after every compile. Calling it with no arguments gives a plain
overview, which is often the most revealing; optionally point it at the doubt with
`target`/`only`, an actuated `pose`, or a specific `question`. Take its flagged
defects seriously and fix them, but do not keep re-critiquing to chase minor polish:
once it reports no serious defects, stop and finish. One or two rounds on the parts
you are unsure about is usually enough.
