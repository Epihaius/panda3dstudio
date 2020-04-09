# This module contains the shaders used to create vertex normal geometry.


VERT_SHADER = """
    #version 330

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec3 p3d_Normal;
    in vec4 p3d_Color;

    out Vertex
    {
        vec3 normal;
        vec4 color;
    } vertex;

    void main()
    {
        gl_Position = p3d_Vertex;
        vertex.normal = p3d_Normal;
        vertex.color = p3d_Color;
    }
"""

GEOM_SHADER = """
    #version 330

    layout(points) in;

    // One line will be generated: 2 vertices
    layout(line_strip, max_vertices=2) out;

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform float normal_length;

    in Vertex
    {
        vec3 normal;
        vec4 color;
    } vertex[];

    out vec4 vertex_color;

    void main()
    {

        vec3 P = gl_in[0].gl_Position.xyz;
        vec3 N = vertex[0].normal;

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(P, 1.0);
        vertex_color = vertex[0].color;
        EmitVertex();

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(P + N * normal_length, 1.0);
        EmitVertex();

        EndPrimitive();

    }
"""

FRAG_SHADER = """
    #version 330

    in vec4 vertex_color;
    layout(location = 0) out vec4 out_color;

    void main()
    {
        out_color = vertex_color;
    }
"""
