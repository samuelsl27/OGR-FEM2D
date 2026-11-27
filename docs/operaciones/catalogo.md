# Catálogo de operaciones

> Spec 006, parte B (RF-6, RF-7). Escrito desde el registro (`ogr_fem2d/api/catalog.py`): un test
> comprueba que esta página es la del código. Las descripciones son las de cada operación, en
> inglés, como las ve un agente por el servidor MCP.

Cada operación se llama igual desde Python (`api.call(ws, nombre, **argumentos)`), la línea de
órdenes (`python -m ogr_fem2d.cli call nombre --json '{…}'`) y el servidor MCP (una herramienta por
operación). Un argumento que no existe se rechaza por su nombre. Los valores van en m, kN, kPa y kN/m³;
la tensión de campo y los resultados, en compresión positiva. «Edita» quiere decir que es un paso de
deshacer (`project_history`).

## analysis

### `analysis_run`

Calculate the model in a child process that can be cancelled; it
writes <model>.h5 beside the model's file. Returns the job_id (and, with
``wait`` seconds, the job's state when it ends or the wait does).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `variant` | `str` | `'reference'` |
| `wait` | `float` | `0.0` |

### `job_cancel`

Stop a job: between two stages within the grace (the stages solved
are written, ``cancelled``), or by killing its process tree (the
results file before stays).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `job_id` | `str` | obligatorio |
| `grace_s` | `float o None` | `None` |

### `job_get`

Where a job is: running (with its progress), done (with its summary:
the results' status, the stages written and why it stopped), failed,
cancelled or crashed (with the end of its log).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `job_id` | `str` | obligatorio |
| `wait` | `float` | `0.0` |

### `job_list`

Every job of this workspace, newest last.

## core

### `project_close`

Close a model, refusing to lose unsaved changes unless told to.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `discard_changes` | `bool` | `False` |

### `project_list`

Every open model.

### `project_new`

Create an empty model and return its project_id.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `name` | `str` | `''` |
| `analysis` | `str` | `'plane_strain'` |
| `units` | `str` | `'metric_kpa'` |

### `project_open`

Open a .ogrfem2d file, or convert a .ogr of OGR Slip2D or a .dxf
into a new model; return its project_id, what is still unfinished in it
(its problems) and, for a conversion, the report of what it did.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `path` | `str` | obligatorio |

### `project_save`

Write the model to its .ogrfem2d (or to ``path``); another existing
file is never replaced unless ``overwrite``.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `path` | `str o None` | `None` |
| `overwrite` | `bool` | `False` |

### `project_settings` (edita)

Change the kind of analysis, the unit system shown (the values do
not change) or the summary, as one undo step.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `analysis` | `str o None` | `None` |
| `units` | `str o None` | `None` |
| `title` | `str o None` | `None` |
| `author` | `str o None` | `None` |
| `date` | `str o None` | `None` |
| `notes` | `str o None` | `None` |

### `project_summary`

What the model holds, the state of its mesh, and its problems.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |

### `project_validate`

Whether the model can be calculated, and every reason it cannot:
its problems, the state of its mesh, the materials without E or nu.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |

## history

### `project_history` (edita)

List, undo or redo edits.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `action` | `str` | `'list'` |
| `steps` | `int` | `1` |

## loads

### `load_delete` (edita)

Delete a load, by its index (project_summary counts them).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `load` | `int` | obligatorio |
| `project_id` | `str o None` | `None` |

### `load_set` (edita)

A distributed load on a stretch of a boundary (kPa, from magnitude to
magnitude_end; normal by default, positive into the ground) or a point
load at a vertex (kN per metre out of plane; vertical by default), with
factor 1 in every stage; with ``load`` (its index), that one is changed.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `kind` | `str` | obligatorio |
| `magnitude` | `float` | obligatorio |
| `project_id` | `str o None` | `None` |
| `boundary` | `str o None` | `None` |
| `start` | `list o None` | `None` |
| `end` | `list o None` | `None` |
| `vertex` | `list o None` | `None` |
| `magnitude_end` | `float o None` | `None` |
| `orientation` | `str o None` | `None` |
| `angle` | `float` | `0.0` |
| `name` | `str` | `''` |
| `load` | `int o None` | `None` |

### `load_stage` (edita)

The factor of a load from ``stage`` on (or in it only): the total
there is factor x magnitude, 0 takes it off.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `load` | `int` | obligatorio |
| `stage` | `str` | obligatorio |
| `factor` | `float` | obligatorio |
| `project_id` | `str o None` | `None` |
| `this_stage_only` | `bool` | `False` |

## mesh

### `mesh_collect` (edita)

Put in the model the mesh a job of ``mesh_generate`` made, as one step
to undo; refused if the job is not done, or if the model changed while
it ran (mesh again).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `job_id` | `str` | obligatorio |

### `mesh_discretize`

The first step of meshing: the nodes every segment of the geometry
will have, with the settings of now, without changing the model.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |

### `mesh_generate` (edita)

Mesh the geometry with its settings, and keep the mesh with the
model; what decided it (the notes of the mesher) and its warnings. With
``background``, in a child process that can be cancelled (job_cancel):
it returns the job_id, and ``mesh_collect`` puts the mesh in the model
when the job is done.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `background` | `bool` | `False` |
| `wait` | `float` | `0.0` |

### `mesh_reset` (edita)

Take the mesh away from the model.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |

### `mesh_settings` (edita)

Change the settings of the mesher (spec 003): kind (graded or
uniform), nodes_per_element (3 or 6), quality_bound (B), boundary_nodes
(graded: nodes on the excavations, or on the external without any),
max_size, size or elements (uniform), windows ([{polygon, size}]).
``clear`` lists the settings to set back to none.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `kind` | `str o None` | `None` |
| `nodes_per_element` | `int o None` | `None` |
| `quality_bound` | `float o None` | `None` |
| `boundary_nodes` | `int o None` | `None` |
| `max_size` | `float o None` | `None` |
| `size` | `float o None` | `None` |
| `elements` | `int o None` | `None` |
| `windows` | `list o None` | `None` |
| `clear` | `list o None` | `None` |

## model

### `boundary_add` (edita)

Draw a boundary (external, material, excavation or stage) through
``points_xy``; ``arcs`` gives the centre of the segments that are arcs
([{"segment": k, "centre": [x, y]}]). Its cuts with the others become
vertices of both, unless cut is false.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `type` | `str` | obligatorio |
| `points_xy` | `list` | obligatorio |
| `project_id` | `str o None` | `None` |
| `name` | `str` | `''` |
| `closed` | `bool o None` | `None` |
| `arcs` | `list o None` | `None` |
| `boundary` | `str o None` | `None` |
| `cut` | `bool` | `True` |

### `boundary_circle` (edita)

Draw a circle as four arcs, by its centre and its radius or a point
it goes through.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `type` | `str` | obligatorio |
| `centre` | `list` | obligatorio |
| `project_id` | `str o None` | `None` |
| `radius` | `float o None` | `None` |
| `through` | `list o None` | `None` |
| `name` | `str` | `''` |
| `boundary` | `str o None` | `None` |
| `cut` | `bool` | `True` |

### `boundary_edit` (edita)

Edit or delete a boundary: delete, rename, change_type, set_closed,
translate, move_vertex (point_xy to to_xy, in every boundary that has
it), insert_vertex (point_xy on segment), delete_vertex (index),
set_arc (segment, centre or null), set_divisions (segment, divisions
or null).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `boundary` | `str` | obligatorio |
| `op` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `name` | `str o None` | `None` |
| `new_type` | `str o None` | `None` |
| `closed` | `bool o None` | `None` |
| `dx` | `float` | `0.0` |
| `dy` | `float` | `0.0` |
| `point_xy` | `list o None` | `None` |
| `to_xy` | `list o None` | `None` |
| `index` | `int o None` | `None` |
| `segment` | `int o None` | `None` |
| `centre` | `any` | `None` |
| `divisions` | `int o None` | `None` |
| `with_dependents` | `bool` | `False` |
| `cut` | `bool` | `True` |

### `condition_default` (edita)

The condition of the external boundary where nothing else is said
(x, y, xy or free).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `kind` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |

### `condition_delete` (edita)

Delete a condition, by its index (project_summary counts them).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `condition` | `int` | obligatorio |
| `project_id` | `str o None` | `None` |

### `condition_set` (edita)

A restraint (x, y, xy), a release (free) or an imposed displacement
(displacement: ux and/or uy in m) on a stretch of a boundary or at a
vertex, in every stage; with ``condition`` (its index), that one is
changed instead.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `kind` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `boundary` | `str o None` | `None` |
| `start` | `list o None` | `None` |
| `end` | `list o None` | `None` |
| `vertex` | `list o None` | `None` |
| `ux` | `float o None` | `None` |
| `uy` | `float o None` | `None` |
| `name` | `str` | `''` |
| `condition` | `int o None` | `None` |

### `condition_stage` (edita)

A restraint active or not from ``stage`` on (or in it only); the
factor of an imposed displacement there (null: it does not act).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `condition` | `int` | obligatorio |
| `stage` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `active` | `bool o None` | `None` |
| `factor` | `any` | `'unchanged'` |
| `this_stage_only` | `bool` | `False` |

### `field_set` (edita)

The field stress, compression positive (kPa): constant (sigma_1,
sigma_3, sigma_z, angle of sigma_1 from x in degrees), or gravity
(surface, strata [{bottom, unit_weight, k, kz}] from the top down).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `kind` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `sigma_1` | `float` | `0.0` |
| `sigma_3` | `float` | `0.0` |
| `sigma_z` | `float` | `0.0` |
| `angle` | `float` | `0.0` |
| `surface` | `float o None` | `None` |
| `strata` | `list o None` | `None` |

### `material_assign` (edita)

The region that holds (x, y) takes ``material`` (one material per
region for the whole analysis until spec 012).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `material` | `str` | obligatorio |
| `x` | `float` | obligatorio |
| `y` | `float` | obligatorio |
| `project_id` | `str o None` | `None` |
| `stage` | `str o None` | `None` |
| `this_stage_only` | `bool` | `False` |

### `material_delete` (edita)

Delete a material no region has.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `material` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |

### `material_set` (edita)

Create a material (without ``material``) or change one: name, E and
nu (kPa; none until given), unit weight (kN/m3), initial loading
(field_stress, field_stress_and_body_force, body_force, none), colour.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `material` | `str o None` | `None` |
| `name` | `str o None` | `None` |
| `E` | `float o None` | `None` |
| `nu` | `float o None` | `None` |
| `unit_weight` | `float o None` | `None` |
| `initial_loading` | `str o None` | `None` |
| `color` | `str o None` | `None` |

### `region_excavate` (edita)

Excavate (or fill) the region that holds (x, y) from ``stage`` on,
or in that stage only.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `x` | `float` | obligatorio |
| `y` | `float` | obligatorio |
| `stage` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `excavated` | `bool` | `True` |
| `this_stage_only` | `bool` | `False` |

### `stage_add` (edita)

Insert a stage at ``index`` (0 is in front; by default the end). It
copies the stage before it, or the first one in front of it.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `index` | `int o None` | `None` |
| `name` | `str` | `''` |
| `stage` | `str o None` | `None` |

### `stage_delete` (edita)

Delete a stage, and its column of every table.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `stage` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |

### `stage_rename` (edita)

Give a stage another name (its id stays).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `stage` | `str` | obligatorio |
| `name` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |

## results

### `results_field`

A quantity ready to be drawn: the triangles of every active element
subdivided (level), their values and the range of the legend
(auto_stage, auto_all or custom). With ``as_arrays`` the arrays as they
are (for the interface, in the same process); otherwise as lists.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `quantity` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `stage` | `str o None` | `None` |
| `level` | `int` | `2` |
| `absolute` | `bool` | `False` |
| `range_mode` | `str` | `'auto_stage'` |
| `low` | `float o None` | `None` |
| `high` | `float o None` | `None` |
| `allow_invalid` | `bool` | `False` |
| `as_arrays` | `bool` | `False` |

### `results_open`

The state of the results beside the model's file (valid, stale,
incomplete, cancelled, missing, damaged), who wrote them, their stages
and what decided them (the values written with them, rule 12).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |

### `results_query`

A quantity along a line or polyline (points_xy; n points along it, or
its vertices), on a boundary (at distance to a side), at every node, at
every integration point, at (x, y) in the stage (at), or at (x, y)
through the stages (history).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `quantity` | `str` | obligatorio |
| `kind` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `stage` | `str o None` | `None` |
| `points_xy` | `list o None` | `None` |
| `n` | `int o None` | `None` |
| `boundary` | `str o None` | `None` |
| `distance` | `float` | `0.0` |
| `side` | `str o None` | `None` |
| `x` | `float o None` | `None` |
| `y` | `float o None` | `None` |
| `allow_invalid` | `bool` | `False` |

### `results_report`

The report of the model and of its results (text or html), and, with
``path``, written to that file; or its sections, each with its key,
title and rows (``sections``: the window says them in the reader's
language, each line carries its code).

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `format` | `str` | `'text'` |
| `path` | `str o None` | `None` |
| `overwrite` | `bool` | `False` |

### `results_summary`

The extremes of each quantity at the points and at the nodes, where
they are; the greatest displacement; the reactions, in total and (with
valid results) by boundary.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `project_id` | `str o None` | `None` |
| `stage` | `str o None` | `None` |
| `quantities` | `list o None` | `None` |
| `allow_invalid` | `bool` | `False` |

### `results_table`

Write a query as a CSV table (spec 005, D15), in the units the model
shows; another existing file is not replaced unless ``overwrite``.

| Argumento | Tipo | Por defecto |
|---|---|---|
| `path` | `str` | obligatorio |
| `quantity` | `str` | obligatorio |
| `kind` | `str` | obligatorio |
| `project_id` | `str o None` | `None` |
| `stage` | `str o None` | `None` |
| `points_xy` | `list o None` | `None` |
| `n` | `int o None` | `None` |
| `boundary` | `str o None` | `None` |
| `distance` | `float` | `0.0` |
| `side` | `str o None` | `None` |
| `x` | `float o None` | `None` |
| `y` | `float o None` | `None` |
| `overwrite` | `bool` | `False` |
| `allow_invalid` | `bool` | `False` |
