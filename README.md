# Panda3D Studio
A general-purpose scene editor for the Panda3D open-source game engine

Currently, the main purpose of this editor is to allow users of Panda3D to create their game models right inside of the game engine itself, without needing external modelling programs.
This should avoid any export/import problems, as models are exported from Panda3D Studio as .bam files, whose data closely mirrors the actual Panda3D structures that are used for rendering.
Hopefully, at some point it will also become a full-fledged level editor.

Requirements:
* Panda3D SDK (development version Panda3D-SDK-1.10.0pre-dafe48a or newer)
* wxPython (version 2.8.x is recommended currently, due to issues with version 3.x).

The functionality of this project is still quite basic, with a lot of important features missing or incomplete, so please don't use it for serious work yet.
It most likely won't even work on anything but Windows at this time, because of some problems with wxPython.


There is no manual yet, but to test the program, you can:

* navigate the scene using the Space bar (either hold it down or tap and release the key to start/end navigation mode) and use left mouse button to orbit, right mouse button to pan and both (or mouse wheel) to zoom;

* create a primitive model using a predefined hotkey (Ctrl-Shift-S for a sphere, Ctrl-Shift-B for a box and Ctrl-Shift-C for a cylinder); primitives can be created interactively by dragging on the grid (read the instructions on the statusbar) or by setting default properties in the Object properties panel and clicking "Create object" in the Creation section;

* transform selected objects using the Transform Toolbar and delete them by pressing the Delete key;

* apply material properties to selected models, using either the Material Toolbar (rotate the Transform Toolbar by clicking the up/down arrows to its right to get to it) or by creating/editing a material in the Materials panel and applying it to the selected models;

* open the UV Editor (Ctrl-U) to control UV-mapping by transforming the UVs;

* turn selected models into editable geometry (the "Make editable" button becomes available in the Object properties panel when primitives of the same type are selected) and edit their subobjects (select, transform and delete vertices, edges and polygons; new polygons can be created interactively - use Ctrl to flip the normal and Shift to control triangulation);

* undo (Ctrl-Z), redo (Ctrl-Shift-Z) and edit the entire non-linear, branching history;

* access the DeepShelf toolbar by hovering the mouse over the down arrow at the top of the GUI; its contents is completely customizable (rightclick for context menus);

* save (Ctrl-S) and load (Ctrl-O) a scene and export selected models (using DeepShelf -> File -> Export).




Feel free to discuss this project in [this topic](https://www.panda3d.org/forums/viewtopic.php?f=6&t=18500) on the Panda3D forums.
