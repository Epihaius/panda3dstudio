# Panda3D Studio
A general-purpose scene editor for the Panda3D open-source game engine

Currently, the main purpose of this editor is to allow users of Panda3D to create their game models right inside of the game engine itself, without needing external modelling programs.
This should avoid any export/import problems, as models are exported from Panda3D Studio as .bam files, whose data closely mirrors the actual Panda3D structures that are used for rendering.
Hopefully, at some point it will also become a full-fledged level editor.

Requirements:
* a recent development version of the Panda3D SDK with Python 3.x support. Please note that Python 2.x is no longer supported by this project!

The functionality of this project is still quite basic, with a lot of important features missing or incomplete, so please don't use it for serious work yet.


There is no manual yet, but to test the program, you can:

* navigate the scene using the Space bar (either hold it down or tap and release the key to start/end navigation mode) and use left mouse button to orbit, right mouse button to pan and both (or mouse wheel) to zoom;

* create a primitive model using a predefined hotkey (e.g. Ctrl-Shift-S for a sphere, Ctrl-Shift-B for a box) or from the Create menu; primitives can be created interactively by dragging on the grid (read the instructions on the statusbar) or by setting default properties in the Object properties control panel and clicking "Create object" in the Creation section;

* transform selected objects using the Transform Toolbar and delete them by pressing the Delete key;

* apply material properties to selected models, using either the Material Toolbar (spin the toolbar bundle containing the Transform Toolbar by clicking/dragging the up/down spinner buttons to its right to get to it) or by creating/editing a material in the Materials control panel and applying it to the selected models;

* open the UV editing interface (Ctrl-U) to control UV-mapping by transforming the UVs;

* unlock the geometry of selected models (the "Unlock geometry" button becomes available in the Object properties control panel when primitives are selected) and edit their subobjects (select, transform and delete vertices, edges and polygons; new polygons can be created interactively - use Ctrl to flip the normal and Shift to control triangulation);

* undo (Ctrl-Z), redo (Ctrl-Shift-Z) and edit the entire non-linear, branching history;

* save (Ctrl-S) and load (Ctrl-O) scenes, export selected models (using menu bar -> File -> Export) and import .bam files (using menu bar -> File -> Import).




Feel free to discuss this project in [this topic](https://www.panda3d.org/forums/viewtopic.php?f=6&t=18500) on the Panda3D forums.
