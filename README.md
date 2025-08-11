# Mesh Creation for SWASH

Package to automatically transform swash input files given in cartesian coordinates to an unstructured mesh produced by gmsh. Mesh is proportional to depth, going from finest near the shore to coarsest at maximum depth. Breakwaters as defined by areas of porosity different from 1 have finest resolution.

## Future Work
- Adapt this package to use parameters given as function or cli arguments instead of reading the SWASH input file so it's usable with any program 
