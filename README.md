# Panda3D Studio
A general-purpose scene editor for the Panda3D open-source game engine

The main purpose of this editor is to allow users of Panda3D to create their game models using the game engine itself, without needing external modelling programs.
This should avoid any export/import problems, as models are exported from Panda3D Studio as .bam files, whose data closely mirrors the actual Panda3D structures that are used for rendering.

Export to .obj files is also supported, which should appeal to those who are primarily interested in creating models for import into any other application that supports this file type.

Currently, only static models can be created and exported. At some point in the future, animation might also be supported.

This project is still missing plenty of features, but it's already possible to do some cool things with it.

Requirements:
* a recent development version of the Panda3D SDK with Python 3.x support (not older than [this one](http://buildbot.panda3d.org/downloads/94571aac93b5948adf0f4530cd6e6690408c6230/)). Please note that Python 2.x is no longer supported by this project!

***
## NOTE
Release v1.0.0 breaks backwards compatibility with release v0.9.0.
Please finish your current projects first and export the models you have created before upgrading.
Also, while version 1.1.0 allows loading v1.0.0 scene files, it will never be possible to edit the UVs of the model primitives loaded from these files, and editing these primitives (such as changing their number of segments) can lead to a crash.
***


There is no manual yet, but to test the program, you can:

* navigate the scene using the Space bar (either hold it down or tap and release the key to start/end navigation mode) and use left mouse button to orbit, right mouse button to pan and both (or mouse wheel) to zoom;

* create a primitive model using a predefined hotkey (e.g. Ctrl-Shift-S for a sphere, Ctrl-Shift-B for a box) or from the Create menu; primitives can be created interactively by dragging on the grid (read the instructions on the statusbar) or by setting default properties in the Object properties control panel and clicking "Create object" in the Creation section;

* transform selected objects using the Transform Toolbar and delete them by pressing the Delete key;

* apply material properties to selected models, using either the Material Toolbar (spin the toolbar bundle containing the Transform Toolbar by clicking/dragging the up/down spinner buttons to its right to get to it) or by creating/editing a material in the Materials control panel and applying it to the selected models;

* open the UV editing interface (Ctrl-U) to control UV-mapping by transforming the UVs;

* unlock the geometry of selected models (the "Unlock geometry" button becomes available in the Object properties control panel when primitives are selected) and edit their subobjects (select, transform and delete vertices, normals, edges and polygons; new polygons can be created interactively - use Ctrl to flip the normal and Shift to control triangulation);

* undo (Ctrl-Z), redo (Ctrl-Y) and edit the entire non-linear, branching history;

* save (Ctrl-S) and load (Ctrl-O) scenes, export selected models (using menu bar -> File -> Export) and import model files (using menu bar -> File -> Import).




Feel free to discuss this project in [this topic](https://discourse.panda3d.org/t/panda3d-studio/15250) on the Panda3D forums.
