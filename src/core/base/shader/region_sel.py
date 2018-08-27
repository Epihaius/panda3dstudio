# This module contains the shaders used to region-select top-level objects.


VERT_SHADER = """
    #version 420

    uniform mat4 p3d_ModelViewProjectionMatrix;
    in vec4 p3d_Vertex;
    uniform int index;
    flat out int oindex;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        oindex = index;
    }
"""

FRAG_SHADER = """
    #version 420

    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {
        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));
    }
"""
