# This module contains the shaders used to render the wireframe of a LockedGeom.


VERT_SHADER = """
    #version 330

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in int sides;

    uniform mat4 p3d_ModelMatrix;

    out Vertex
    {
        vec4 color;
        int side_gen;
    } vertex;

    void main()
    {
        gl_Position = p3d_ModelMatrix * p3d_Vertex;
        vertex.color = p3d_Color;
        vertex.side_gen = sides;
    }
"""

GEOM_SHADER = """
    #version 330

    layout(triangles) in;

    // Three lines will be generated: 6 vertices
    layout(line_strip, max_vertices=6) out;

    uniform mat4 p3d_ViewProjectionMatrix;
    uniform mat4 p3d_ViewMatrixInverse;
    uniform mat4 p3d_ProjectionMatrix;
    uniform bool inverted;
    uniform bool two_sided;

    in Vertex
    {
        vec4 color;
        int side_gen;
    } vertex[];

    out vec4 vertex_color;

    void main()
    {

        vertex_color = vertex[0].color;

        int side_generation, S0, S1, S2;
        int sides[3];

        // determine which sides should be generated (1) or not (0)
        side_generation = vertex[0].side_gen;
        S0 = side_generation >> 2;
        S1 = (side_generation ^ (S0 << 2)) >> 1;
        S2 = side_generation ^ (S0 << 2) ^ (S1 << 1);
        sides = int[] (S0, S1, S2);

        vec3 P0 = gl_in[0].gl_Position.xyz;
        vec3 P1 = gl_in[1].gl_Position.xyz;
        vec3 P2 = gl_in[2].gl_Position.xyz;
        vec3 pos[4] = vec3[] (P0, P1, P2, P0);
        vec3 V0 = P1 - P0;
        vec3 V1 = P2 - P1;
        vec3 face_normal = inverted ? cross(V1, V0) : cross(V0, V1);
        vec3 vec;

        // a face whose normal points away from the camera is not rendered;
        // this is determined by the dot product of the face normal and the
        // following vector:
        if (p3d_ProjectionMatrix[3].w == 1.)
            // orthographic lens;
            // use inverted camera direction vector
            vec = p3d_ViewMatrixInverse[2].xyz;
        else
            // perspective lens;
            // compute vector pointing from any point of triangle to camera origin
            vec = p3d_ViewMatrixInverse[3].xyz - P0;

        if (two_sided || dot(vec, face_normal) >= 0.) {

            // generate sides
            for (int i = 0; i < 3; ++i)
            {
                for (int j = 0; j < sides[i]; ++j)
                {

                    gl_Position = p3d_ViewProjectionMatrix * vec4(pos[i], 1.0);
                    EmitVertex();

                    gl_Position = p3d_ViewProjectionMatrix * vec4(pos[i + 1], 1.0);
                    EmitVertex();

                    EndPrimitive();

                }
            }

        }

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
