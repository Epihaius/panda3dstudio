# This module contains the vertex shader used to region-select point-helper objects.
# The needed fragment shader can be found in the "region_sel.py" module of this package.


VERT_SHADER = """
    #version 420

    uniform mat4 p3d_ModelViewProjectionMatrix;
    in vec4 p3d_Vertex;
    in float size;
    in int index;
    uniform int index_offset;
    flat out int oindex;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        gl_PointSize = size;
        oindex = index + index_offset;
    }
"""
