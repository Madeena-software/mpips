# Pipeline control flow

The Pipeline Builder supports ordinary acyclic pipelines, True/False branches,
and explicit bounded loops. Existing `/pipelines/dag/...` URLs and graph JSON stay compatible.

## Repeat until a condition is met

In MIPC, import `docs/pipeline-control-flow-example.json` into a new test pipeline, or wire:

1. Input → Loop **Initial**.
2. Loop **Current iteration** → processing nodes → Condition image input.
3. Condition **True** → Loop **Stop**.
4. Condition **False** → Loop **Repeat**.
5. Loop **Final result** → Output.

Set the Condition expression, for example `iteration >= 3` or
`iteration > 1 and delta_entropy < 0.01`. Set Loop `max_iterations` (1–100,
default 10). The first processing pass is iteration 1. The final image is emitted
only when Stop is active or the hard limit is reached. Exactly one Stop/Repeat
image must be active each pass. Final metadata distinguishes `condition` from
`iteration_limit` and records gate choices and iteration count.

`result_mode=latest` returns the last pass. `best` selects the first best-scoring
processed image across passes using `score_metric=mean|std|entropy` and
`score_direction=maximize|minimize`. The initial seed is not a candidate.

## Branch without repeating

Condition routes its image to one True/False output. Connect those paths through
processing nodes, then to Branch Merge's True/False inputs. Branch Merge passes
the single active image; inactive paths skip processing. Two active inputs are
an error. Use the existing Merge node when you intend to blend images.

## Expressions and limits

Conditions support numeric and `True`/`False` literals, parentheses, arithmetic
`+ - * / %`, comparisons `< <= > >= == !=`, and `and or not`. Expressions are
limited to 512 characters and 60 tokens. Calls, attributes, indexing and code
execution are rejected. A condition must produce a boolean.

Variables: `iteration`, `mean`, `std`, `entropy`; optional scalar input `value`;
`previous_value`, `delta_value`, `delta_mean`, `delta_std`, `delta_entropy`.
Deltas are absolute changes from the same gate's previous active iteration.
Guard previous/delta values with `iteration > 1 and ...`; history resets per loop
run. Outside a loop, iteration is 1. Measurements use the current image's raw
values; entropy uses 256 bins over its current range. These scores express image
statistics, not diagnostic quality.

Only Loop Repeat/Stop connections allow cycles. Sequential/disjoint loops are
supported; nested/crossing loops and IO inside repeated bodies are rejected.
Route body exits through Loop Final result. At most 1000 nodes and 10000 estimated
stage visits are allowed. Controls run on the scientific server; browser fallback
rejects them. Cancellation and temporary-file cleanup use the existing executor.
