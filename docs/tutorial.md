# Creating Unstructured Grids for SWASH using Gmsh

A comprehensive tutorial for coastal engineering applications

## Table of Contents

1. [Introduction: Why Unstructured Meshes?](#introduction)
2. [Understanding Gmsh Fundamentals](#gmsh-fundamentals)
3. [Setting Up Your Workspace](#workspace-setup)
4. [Creating Your First Mesh](#first-mesh)
5. [Incorporating Bathymetry Data](#bathymetry-integration)
6. [Mesh Refinement Strategies](#refinement-strategies)
7. [Exporting for SWASH](#swash-export)
8. [Quality Control and Validation](#quality-control)
9. [Advanced Techniques](#advanced-techniques)
10. [Troubleshooting Common Issues](#troubleshooting)

---

## 1. Introduction: Why Unstructured Meshes? {#introduction}

### The Coastal Engineering Context

When modelling wave interactions with breakwaters in locations like the Côte-Nord of the Saint-Laurent, you need to capture:
- Complex shoreline geometries
- Varying water depths (bathymetry)
- Detailed structures (breakwaters, piers)
- Multiple length scales (from large offshore waves to small-scale turbulence)

**Structured vs Unstructured Grids:**
- **Structured grids** (regular rectangles): Simple but wasteful - must use fine resolution everywhere
- **Unstructured grids** (triangular elements): Adaptive - fine where needed, coarse where possible

### Why Gmsh + SWASH?

- **Gmsh**: Open-source mesh generator with powerful geometry tools
- **SWASH**: Non-hydrostatic wave model supporting unstructured triangular meshes
- **Integration**: SWASH can directly read Gmsh's output format

---

## 2. Understanding Gmsh Fundamentals {#gmsh-fundamentals}

### Core Concepts

**Geometric Hierarchy** (bottom-up):
1. **Points**: 0D entities (coordinates)
2. **Curves**: 1D entities (lines, arcs)
3. **Surfaces**: 2D entities (enclosed by curves)
4. **Volumes**: 3D entities (enclosed by surfaces)

**Physical Groups**: 
- Assign names/IDs to geometric entities
- Essential for boundary conditions in SWASH
- Examples: "inlet", "outlet", "breakwater", "shoreline"

**Mesh Elements**:
- **Lines**: 1D elements along curves
- **Triangles**: 2D elements within surfaces
- **Tetrahedra**: 3D elements within volumes (not used in SWASH 2D)

### File Types

- `.geo`: Gmsh geometry/mesh script (human-readable)
- `.msh`: Gmsh mesh output (binary or ASCII)
- `.node/.ele`: Triangle format (SWASH can read via READGRID UNSTRUCTURED)

---

## 3. Setting Up Your Workspace {#workspace-setup}

### Installation

1. **Download Gmsh**: Visit [gmsh.info](https://gmsh.info) and download for your platform
2. **Verify Installation**: 
   ```bash
   gmsh --version
   ```

### Directory Structure

Create a project directory:
```
breakwater_project/
├── bathymetry/
│   ├── raw_data.txt
│   └── processed_bathy.pos
├── geometry/
│   ├── domain.geo
│   └── breakwater.geo
├── meshes/
│   ├── coarse_mesh.msh
│   └── refined_mesh.msh
└── swash/
    ├── input_files/
    └── results/
```

### Essential Files for Our Tutorial

You'll need:
- Bathymetry data (XYZ format: longitude, latitude, depth)
- Coastline data (optional but helpful)
- Breakwater geometry specifications

---

## 4. Creating Your First Mesh {#first-mesh}

### Step 1: Basic Domain Definition

Create `simple_domain.geo`:

```geo
// Simple rectangular domain for Côte-Nord application
// Units: All dimensions in metres

// Define characteristic lengths
lc_coarse = 100.0;  // Offshore element size
lc_fine = 10.0;     // Nearshore element size

// Domain boundaries (example coordinates)
Point(1) = {-2000, -1000, 0, lc_coarse};  // SW corner
Point(2) = { 2000, -1000, 0, lc_coarse};  // SE corner  
Point(3) = { 2000,  1000, 0, lc_coarse};  // NE corner
Point(4) = {-2000,  1000, 0, lc_coarse};  // NW corner

// Create boundary lines
Line(1) = {1, 2};  // South boundary
Line(2) = {2, 3};  // East boundary
Line(3) = {3, 4};  // North boundary
Line(4) = {4, 1};  // West boundary

// Create surface
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Define physical groups for SWASH boundary conditions
Physical Curve("inlet") = {4};     // West (wave input)
Physical Curve("outlet") = {2};    // East (wave output)
Physical Curve("north_wall") = {3}; // North boundary
Physical Curve("south_wall") = {1}; // South boundary

// Physical surface for the computational domain
Physical Surface("water") = {1};
```

### Step 2: Mesh Generation

**Using Gmsh GUI:**
1. Open Gmsh
2. File → Open → `simple_domain.geo`
3. Mesh → 2D
4. View the result

**Using Command Line:**
```bash
gmsh -2 simple_domain.geo -o simple_domain.msh
```

### Step 3: Understanding the Output

The `.msh` file contains:
- Node coordinates
- Element connectivity (which nodes form each triangle)
- Physical group assignments

---

## 5. Incorporating Bathymetry Data {#bathymetry-integration}

### Understanding Bathymetry Integration

Bathymetry affects mesh generation in two ways:
1. **Mesh density**: Shallower areas often need finer meshes
2. **Node elevations**: Each mesh node needs a depth value

### Step 1: Prepare Bathymetry Data

Convert your bathymetry to Gmsh `.pos` format:

```python
# Python script to convert XYZ bathymetry to Gmsh .pos format
import numpy as np

def xyz_to_pos(xyz_file, pos_file):
    """Convert XYZ bathymetry data to Gmsh .pos format"""
    data = np.loadtxt(xyz_file)
    x, y, z = data[:, 0], data[:, 1], data[:, 2]
    
    with open(pos_file, 'w') as f:
        f.write('View "Bathymetry" {\n')
        for i in range(len(x)):
            f.write(f'SP({x[i]}, {y[i]}, 0) {{{z[i]}}};\n')
        f.write('};\n')

# Usage
xyz_to_pos('bathymetry_data.txt', 'bathymetry.pos')
```

### Step 2: Bathymetry-Driven Mesh Sizing

Create `domain_with_bathy.geo`:

```geo
// Include the bathymetry data
Merge "bathymetry.pos";

// Basic domain points (as before)
Point(1) = {-2000, -1000, 0, 100};
Point(2) = { 2000, -1000, 0, 100};
Point(3) = { 2000,  1000, 0, 100};
Point(4) = {-2000,  1000, 0, 100};

// Boundary lines and surface (as before)
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Mesh size field based on bathymetry
Field[1] = PostView;
Field[1].ViewIndex = 0;  // Index of bathymetry view
Field[1].ViewTag = 0;

// Transform depth to mesh size
Field[2] = MathEval;
Field[2].F = "10 + 0.1 * F1";  // Size = 10m + 10% of depth

// Set the background field
Background Field = 2;

// Physical groups
Physical Curve("inlet") = {4};
Physical Curve("outlet") = {2};
Physical Curve("north_wall") = {3};
Physical Curve("south_wall") = {1};
Physical Surface("water") = {1};
```

### Step 3: Adding Coastal Features

```geo
// Add breakwater geometry
bw_x = 500;   // Breakwater x-position
bw_y1 = -200; // Breakwater start y
bw_y2 = 200;  // Breakwater end y
bw_lc = 5;    // Fine mesh around breakwater

Point(10) = {bw_x, bw_y1, 0, bw_lc};
Point(11) = {bw_x, bw_y2, 0, bw_lc};
Line(10) = {10, 11};

// Embed the breakwater in the surface
Line{10} In Surface{1};

// Physical group for breakwater
Physical Curve("breakwater") = {10};
```

---

## 6. Mesh Refinement Strategies {#refinement-strategies}

### Local Refinement Around Structures

```geo
// Distance-based refinement around breakwater
Field[3] = Distance;
Field[3].CurvesList = {10};  // Breakwater line

Field[4] = Threshold;
Field[4].InField = 3;
Field[4].SizeMin = 2.0;   // 2m elements near breakwater
Field[4].SizeMax = 50.0;  // 50m elements far from breakwater
Field[4].DistMin = 20.0;  // Start transition at 20m
Field[4].DistMax = 200.0; // End transition at 200m

// Combine with bathymetry field
Field[5] = Min;
Field[5].FieldsList = {2, 4};  // Take minimum of bathymetry and distance fields

Background Field = 5;
```

### Wave Length Considerations

For coastal wave modelling, you need approximately 10-20 elements per wavelength:

```geo
// Function to estimate element size based on water depth
// Using shallow water wave theory: L = T * sqrt(g * h)
// For T = 8s (typical wave period), g = 9.81 m/s²

Field[6] = MathEval;
Field[6].F = "Min(50, Max(2, sqrt(9.81 * Abs(F1)) * 8 / 15))";
// Element size = wavelength / 15, constrained between 2m and 50m
```

---

## 7. Exporting for SWASH {#swash-export}

### Gmsh Mesh Formats for SWASH

SWASH supports two unstructured formats:
1. **Triangle format**: `.node` and `.ele` files
2. **Easymesh format**: `.n` and `.e` files

### Export to Triangle Format

```bash
# Generate mesh and convert to Triangle format
gmsh -2 -format msh2 domain_with_bathy.geo

# Convert using Gmsh's built-in converter
gmsh domain_with_bathy.msh -save_all -format mesh -o domain.mesh
```

Or use the GUI:
1. File → Export
2. Choose format: "Triangle"
3. Save as `domain.node` and `domain.ele`

### SWASH Input File Configuration

Create `swash_input.swn`:

```fortran
PROJECT 'BreakwaterStudy' '001'
        'Wave interaction with breakwater'
        'Côte-Nord application'
        'Unstructured mesh test'

SET level=0.0 nor=90.0

MODE NONSTATIONARY TWODIMENSIONAL

COORDINATES CARTESIAN

CGRID UNSTRUCTURED

READGRID UNSTRUCTURED TRIANGLE 'domain'

VERT 2 PERC 50 PERC 50

INPGRID BOTTOM UNSTRUCTURED EXCEPTION -999
READINP BOTTOM 1.0 'bathymetry.bot' 4 0 FREE

! Boundary conditions
BOUNDCOND SIDE 1 BTYPE WEAKREFL CON REG 1.5 8.0 270.0
BOUNDCOND SIDE 2 BTYPE SOMMERFELD
BOUNDCOND SIDE 3 BTYPE VEL CON 0.0
BOUNDCOND SIDE 4 BTYPE VEL CON 0.0

! Output
POINTS 'P1' 0 0
TABLE 'P1' HEADER 'output.tab' TIME WATL VEL

COMPUTE 0 0.1 SEC 100
STOP
```

### Bathymetry Interpolation

After mesh generation, interpolate bathymetry to mesh nodes:

```python
import numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import griddata

def interpolate_bathymetry_to_mesh(bathy_file, node_file, output_file):
    """Interpolate bathymetry data to unstructured mesh nodes"""
    
    # Load bathymetry data
    bathy_data = np.loadtxt(bathy_file)
    bathy_x, bathy_y, bathy_z = bathy_data[:, 0], bathy_data[:, 1], bathy_data[:, 2]
    
    # Load mesh nodes
    with open(node_file, 'r') as f:
        lines = f.readlines()
    
    # Parse node file (Triangle format)
    n_nodes = int(lines[0].split()[0])
    mesh_nodes = np.zeros((n_nodes, 2))
    
    for i in range(1, n_nodes + 1):
        parts = lines[i].split()
        mesh_nodes[i-1, 0] = float(parts[1])  # x
        mesh_nodes[i-1, 1] = float(parts[2])  # y
    
    # Interpolate bathymetry to mesh nodes
    mesh_depths = griddata(
        (bathy_x, bathy_y), bathy_z, 
        (mesh_nodes[:, 0], mesh_nodes[:, 1]), 
        method='linear', fill_value=-999
    )
    
    # Write SWASH bathymetry file
    with open(output_file, 'w') as f:
        for depth in mesh_depths:
            f.write(f'{depth}\n')

# Usage
interpolate_bathymetry_to_mesh(
    'bathymetry_data.txt', 
    'domain.node', 
    'bathymetry.bot'
)
```

---

## 8. Quality Control and Validation {#quality-control}

### Mesh Quality Metrics

**In Gmsh GUI:**
1. Tools → Options → Mesh → Visibility
2. Check "Element quality" and "View element quality"

**Quality indicators:**
- **Aspect ratio**: < 3 is good, > 10 is problematic
- **Minimum angle**: > 15° preferred
- **Maximum angle**: < 150° preferred

### Validation Checklist

- [ ] All boundaries have physical groups assigned
- [ ] Mesh density adequate for wave resolution (λ/10 to λ/20)
- [ ] No degenerate triangles (zero area)
- [ ] Bathymetry properly interpolated
- [ ] Boundary markers correctly numbered
- [ ] File formats compatible with SWASH

### Common Issues and Fixes

**Problem**: Distorted elements near boundaries
**Solution**: Add intermediate points along curves

```geo
// Instead of direct line
Line(1) = {1, 2};

// Use spline with intermediate points
Point(5) = {-1000, -1000, 0, 50};
Point(6) = {    0, -1000, 0, 25};
Point(7) = { 1000, -1000, 0, 50};
Spline(1) = {1, 5, 6, 7, 2};
```

**Problem**: Excessive refinement
**Solution**: Limit minimum element size

```geo
Mesh.CharacteristicLengthMin = 1.0;  // Minimum 1m elements
Mesh.CharacteristicLengthMax = 100.0; // Maximum 100m elements
```

---

## 9. Advanced Techniques {#advanced-techniques}

### Boundary Layer Meshing

For detailed flow near structures:

```geo
Field[7] = BoundaryLayer;
Field[7].CurvesList = {10};  // Breakwater
Field[7].Size = 0.5;         // First layer thickness
Field[7].Thickness = 10;     // Total boundary layer thickness
Field[7].Ratio = 1.2;        // Growth ratio
Field[7].AnisoMax = 10;      // Maximum anisotropy
```

### Multi-Scale Domains

For linking 1D (flume) and 2D (prototype) models:

```geo
// 1D section extraction
Point(20) = {-500, 0, 0, 5};
Point(21) = { 500, 0, 0, 5};
Line(20) = {20, 21};

Physical Curve("flume_section") = {20};
```

### Parametric Geometry

For testing different breakwater configurations:

```geo
// Parametric breakwater definition
bw_length = 400;
bw_angle = 15;  // degrees from normal
bw_gap = 50;    // gap in breakwater

x1 = bw_x - bw_length/2 * Cos(bw_angle * Pi/180);
y1 = -bw_length/2 * Sin(bw_angle * Pi/180);
x2 = bw_x - bw_gap/2 * Cos(bw_angle * Pi/180);
y2 = -bw_gap/2 * Sin(bw_angle * Pi/180);
// ... continue for segmented breakwater
```

---

## 10. Troubleshooting Common Issues {#troubleshooting}

### Gmsh-Specific Problems

**Error**: "Surface mesh could not be generated"
**Causes**: 
- Self-intersecting curves
- Inconsistent curve orientations
- Characteristic length too small

**Solutions**:
```geo
// Check curve orientations
Curve Loop(1) = {1, 2, 3, 4};  // Counterclockwise
// Add tolerance
Geometry.Tolerance = 1e-6;
```

**Error**: "No elements in mesh"
**Cause**: Missing surface definition
**Solution**: Ensure Physical Surface is defined

### SWASH Integration Issues

**Error**: "Cannot read unstructured grid"
**Solutions**:
- Verify file format (Triangle vs Easymesh)
- Check boundary marker numbering
- Ensure counterclockwise node ordering

**Error**: "Exception values in bathymetry"
**Solution**: Check interpolation coverage
```python
# Identify nodes without bathymetry data
missing_indices = np.where(mesh_depths == -999)[0]
print(f"Missing bathymetry at {len(missing_indices)} nodes")
```

### Performance Optimisation

**Large mesh handling**:
- Use binary mesh format
- Enable parallel mesh generation:
```bash
gmsh -nt 4 -2 domain.geo  # Use 4 threads
```

**Memory management**:
- Split large domains into subdomains
- Use mesh coarsening in deep water

---

## Summary

This tutorial covered:
1. **Conceptual foundation**: Why unstructured meshes matter for coastal engineering
2. **Gmsh basics**: Geometry creation, mesh generation, and quality control
3. **Bathymetry integration**: Data conversion and mesh adaptation
4. **SWASH compatibility**: File formats and boundary conditions
5. **Advanced techniques**: Refinement strategies and optimisation

### Next Steps

1. **Practice**: Start with simple rectangular domains
2. **Experiment**: Try different refinement strategies
3. **Validate**: Compare results with structured grid solutions
4. **Iterate**: Refine based on wave resolution requirements

### Key Takeaways

- **Start simple**: Basic geometry first, add complexity gradually
- **Plan refinement**: Know where you need resolution before meshing
- **Validate early**: Check mesh quality before long SWASH runs
- **Document choices**: Keep track of mesh parameters for reproducibility

Remember: mesh generation is both an art and a science. The "best" mesh depends on your specific application, computational resources, and accuracy requirements. Start with the guidelines provided here, then adapt based on your results.

---

*Good luck with your breakwater modelling project! The combination of Gmsh's flexibility and SWASH's non-hydrostatic capabilities should serve you well for both 1:2 scale laboratory tests and full-scale prototype simulations.*