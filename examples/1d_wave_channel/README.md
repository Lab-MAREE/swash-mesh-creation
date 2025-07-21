# 1D Example

Using a bathymetry with a breakwater, create a mesh that can then bad applied to the wave channel without the breakwater.

## Usage

Create the mesh :

```
sm create bathymetry_with_breakwater.txt
```

Apply the mesh :

```
sm apply mesh.msh INPUT bathymetry.txt --in-place
```
