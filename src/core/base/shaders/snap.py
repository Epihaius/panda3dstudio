# This module contains the shaders used to render snap point coordinates.


# The shaders for snapping to a vertex.

VERT_SHADER_V = """
    #version 330

    uniform mat4 p3d_ModelMatrix;
    in vec4 p3d_Vertex;

    void main() {
        gl_Position = p3d_ModelMatrix * p3d_Vertex;
    }
"""

GEOM_SHADER_V = """
    #version 330

    layout(triangles) in;

    // Three points will be generated: 3 vertices
    layout(points, max_vertices=3) out;

    uniform mat4 p3d_ViewProjectionMatrix;
    uniform mat4 p3d_ViewMatrixInverse;
    uniform mat4 p3d_ProjectionMatrix;
    uniform bool inverted;
    uniform bool two_sided;

    out vec3 snap_coords;

    void main()
    {

        vec3 P0 = gl_in[0].gl_Position.xyz;
        vec3 P1 = gl_in[1].gl_Position.xyz;
        vec3 P2 = gl_in[2].gl_Position.xyz;
        vec3 positions[3] = vec3[] (P0, P1, P2);
        vec3 V0 = P1 - P0;
        vec3 V1 = P2 - P1;
        vec3 face_normal = inverted ? cross(V1, V0) : cross(V0, V1);
        vec3 vec;

        if (p3d_ProjectionMatrix[3].w == 1.)
            // orthographic lens;
            // use inverted camera direction vector
            vec = p3d_ViewMatrixInverse[2].xyz;
        else
            // perspective lens;
            // compute vector pointing from any point of triangle to camera origin
            vec = p3d_ViewMatrixInverse[3].xyz - P0;

        if (two_sided || dot(vec, face_normal) >= 0.) {
            // generate points
            for (int i = 0; i < 3; ++i)
            {
                gl_Position = p3d_ViewProjectionMatrix * vec4(positions[i], 1.0);
                snap_coords = positions[i];
                EmitVertex();
                EndPrimitive();
            }
        }

    }
"""


# The shaders for snapping to an edge midpoint.

VERT_SHADER_E = """
    #version 330

    uniform mat4 p3d_ModelMatrix;
    in vec4 p3d_Vertex;
    in int sides;

    out Vertex
    {
        int side_gen;
    } vertex;

    void main() {
        gl_Position = p3d_ModelMatrix * p3d_Vertex;
        vertex.side_gen = sides;
    }
"""

GEOM_SHADER_E = """
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
        int side_gen;
    } vertex[];

    out vec3 snap_coords;

    void main()
    {

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
        vec3 positions[4] = vec3[] (P0, P1, P2, P0);
        vec3 V0 = P1 - P0;
        vec3 V1 = P2 - P1;
        vec3 face_normal = inverted ? cross(V1, V0) : cross(V0, V1);
        vec3 vec;

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

                    snap_coords = (positions[i] + positions[i + 1]) * .5;

                    gl_Position = p3d_ViewProjectionMatrix * vec4(positions[i], 1.0);
                    EmitVertex();

                    gl_Position = p3d_ViewProjectionMatrix * vec4(positions[i + 1], 1.0);
                    EmitVertex();

                    EndPrimitive();

                }
            }
        }

    }
"""


# The shaders for snapping to a polygon center.

VERT_SHADER_P = """
    #version 330

    uniform mat4 p3d_ModelMatrix;
    in vec4 p3d_Vertex;
    in vec3 snap_pos;

    out Vertex
    {
        vec3 snap_pos;
    } vertex;

    void main() {
        gl_Position = p3d_ModelMatrix * p3d_Vertex;
        vertex.snap_pos = (p3d_ModelMatrix * vec4(snap_pos, 1.)).xyz;
    }
"""

GEOM_SHADER_P = """
    #version 330

    layout(triangles) in;

    // One triangles will be generated: 3 vertices
    layout(triangle_strip, max_vertices=3) out;

    uniform mat4 p3d_ViewProjectionMatrix;
    uniform mat4 p3d_ViewMatrixInverse;
    uniform mat4 p3d_ProjectionMatrix;
    uniform bool inverted;
    uniform bool two_sided;

    in Vertex
    {
        vec3 snap_pos;
    } vertex[];

    out vec3 snap_coords;

    void main()
    {

        vec3 P0, P1, P2;
        snap_coords = vertex[0].snap_pos;

        if (inverted) {
            P0 = gl_in[2].gl_Position.xyz;
            P1 = gl_in[1].gl_Position.xyz;
            P2 = gl_in[0].gl_Position.xyz;
        }
        else {
            P0 = gl_in[0].gl_Position.xyz;
            P1 = gl_in[1].gl_Position.xyz;
            P2 = gl_in[2].gl_Position.xyz;
        }
        vec3 positions[3] = vec3[] (P0, P1, P2);
        vec3 V0 = P1 - P0;
        vec3 V1 = P2 - P1;
        vec3 face_normal = cross(V0, V1);
        vec3 vec;

        if (p3d_ProjectionMatrix[3].w == 1.)
            // orthographic lens;
            // use inverted camera direction vector
            vec = p3d_ViewMatrixInverse[2].xyz;
        else
            // perspective lens;
            // compute vector pointing from any point of triangle to camera origin
            vec = p3d_ViewMatrixInverse[3].xyz - P0;

        if (two_sided || dot(vec, face_normal) >= 0.) {
            for (int i = 0; i < 3; ++i)
            {
                gl_Position = p3d_ViewProjectionMatrix * vec4(positions[i], 1.0);
                EmitVertex();
            }
            EndPrimitive();
        }

    }
"""


FRAG_SHADER = """
    #version 330

    uniform float snap_type_id;
    in vec3 snap_coords;

    layout(location = 0) out vec4 out_color;

    void main() {
        // output the snap point coordinates as a color value
        out_color = vec4(snap_coords, snap_type_id);
    }
"""
