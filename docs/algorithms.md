# Printability Checks

The `check` command runs eight detectors against a mesh, each reporting a
severity (error / warning / info) and an actionable fix. Every conclusion is
explainable — no black box.

## The detectors

### Watertightness
A watertight mesh has no holes: every edge is shared by exactly two faces.
Non-watertight meshes leak and slice incorrectly.

```python
mesh.is_watertight
```

### Manifoldness
A manifold mesh has every edge belonging to two triangles. Non-manifold edges
(three or more faces on one edge) cause slicing errors.

```python
mesh.is_volume
```

### Degenerate faces
Triangles with near-zero area (slivers) break slicing and mesh operations.

```python
areas = mesh.area_faces
slivers = areas < 1e-10
```

### Inverted normals
Faces whose winding order points inward. Inconsistent normals cause the slicer
to treat inside/outside wrongly.

```python
mesh.is_winding_consistent
```

### Thin walls
Walls thinner than a material's minimum wall thickness are too weak to print.
We sample points on the surface and **cast rays along the inward normal**,
measuring distance to the opposite surface — a real thickness estimate, not a
bounding-box heuristic.

```python
points, faces = trimesh.sample.sample_surface(mesh, N)
origins = points - normals * 1e-4
locations, idx, _ = mesh.ray.intersects_location(origins, -normals)
# distance < min_thickness => thin wall
```

### Overhangs
Faces whose normals point downward and whose overhang angle (from horizontal)
is below the threshold need support. We only consider downward faces — the
print bed contact is not misreported.

```python
nz = mesh.face_normals[:, 2]
downward = nz < 0
angle = degrees(arccos(-nz[downward]))  # 0° = flat down, worst
overhang = angle < max_angle
```

### Self-intersections
Faces that penetrate each other cannot be sliced. We find candidate pairs with
an R-tree over triangle bounding boxes, then confirm with an exact
Möller-Trumbore segment-triangle test.

```python
tree = mesh.triangles_tree          # R-tree over triangle AABBs
# for each overlapping pair:
#   segment-triangle intersection test
```

### Isolated components
Disconnected shells print as separate pieces. Reported when the mesh has more
than one connected body.

## Scoring

Each issue subtracts from 100:

| Severity | Penalty |
|---|---|
| error | 20 |
| warning | 10 |
| info | 5 |

The final score is `max(0, 100 - penalties)`. A healthy model scores 90-100.

## Design principles

- **No black box** — every issue carries an evidence description and a fix.
- **Vendor-neutral** — thresholds come from profiles, not hardcoded brands.
- **Lightweight** — uses `trimesh` + `numpy`, no heavy geometry kernel.
