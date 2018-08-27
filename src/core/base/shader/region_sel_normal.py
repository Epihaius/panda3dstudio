# This module contains the vertex and geometry shaders used to region-select normals.
# The needed fragment shader can be found in the "region_sel.py" module of this package.


VERT_SHADER = """
    #version 420

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec3 p3d_Normal;
    in int index;
    uniform int index_offset;

    out Vertex
    {
        vec3 normal;
        int index;
    } vertex;

    void main()
    {
        gl_Position = p3d_Vertex;
        vertex.normal = p3d_Normal;
        vertex.index = index + index_offset;
    }
"""

GEOM_SHADER = """
    #version 420

    layout(points) in;

    // Three lines will be generated: 6 vertices
    layout(line_strip, max_vertices=2) out;

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform float normal_length;

    in Vertex
    {
        vec3 normal;
        int index;
    } vertex[];

    flat out int oindex;

    void main()
    {

        oindex = vertex[0].index;

        vec3 P = gl_in[0].gl_Position.xyz;
        vec3 N = vertex[0].normal;

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(P, 1.0);
        EmitVertex();

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(P + N * normal_length, 1.0);
        EmitVertex();

        EndPrimitive();

    }
"""
