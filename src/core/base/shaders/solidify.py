# This module contains the shaders used to preview model surface solidification.

from .extrusion_inset import FRAG_SHADER


VERT_SHADER = """
    #version 330

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec3 p3d_Normal;
    in vec4 p3d_Color;
    in int sides;
    in vec3 extrusion_vec;

    out Vertex
    {
        vec3 normal;
        vec4 color;
        int side_gen;
        vec3 extr_vec;
    } vertex;

    void main()
    {
        gl_Position = p3d_Vertex;
        vertex.normal = p3d_Normal;
        vertex.color = p3d_Color;
        vertex.side_gen = sides;
        vertex.extr_vec = extrusion_vec;
    }
"""

GEOM_SHADER = """
    #version 330

    layout(triangles) in;

    // Top and bottom triangles and a maximum of three side quads will be generated: 18 vertices
    layout(triangle_strip, max_vertices=18) out;

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform float thickness;
    uniform float offset;

    in Vertex
    {
        vec3 normal;
        vec4 color;
        int side_gen;
        vec3 extr_vec;
    } vertex[];

    out vec4 g_color;
    out vec3 eye_vec;
    out vec3 eye_normal;

    void main()
    {

        g_color = vertex[0].color;

        float vec_len = offset - thickness * .5;

        vec3 P0 = gl_in[0].gl_Position.xyz + vertex[0].extr_vec * vec_len;
        vec3 P1 = gl_in[1].gl_Position.xyz + vertex[1].extr_vec * vec_len;
        vec3 P2 = gl_in[2].gl_Position.xyz + vertex[2].extr_vec * vec_len;
        vec3 P3 = P0 + vertex[0].extr_vec * thickness;
        vec3 P4 = P1 + vertex[1].extr_vec * thickness;
        vec3 P5 = P2 + vertex[2].extr_vec * thickness;
        vec4 PP0 = p3d_ModelViewProjectionMatrix * vec4(P0, 1.0);
        vec4 PP1 = p3d_ModelViewProjectionMatrix * vec4(P1, 1.0);
        vec4 PP2 = p3d_ModelViewProjectionMatrix * vec4(P2, 1.0);
        vec4 PP3 = p3d_ModelViewProjectionMatrix * vec4(P3, 1.0);
        vec4 PP4 = p3d_ModelViewProjectionMatrix * vec4(P4, 1.0);
        vec4 PP5 = p3d_ModelViewProjectionMatrix * vec4(P5, 1.0);
        vec3 pos[8] = vec3[] (P0, P1, P2, P0, P3, P4, P5, P3);
        vec4 proj_pos[8] = vec4[] (PP0, PP1, PP2, PP0, PP3, PP4, PP5, PP3);

        int side_generation, S0, S1, S2;
        int sides[3];

        // determine which sides should be generated (1) or not (0)
        side_generation = vertex[0].side_gen;
        S0 = side_generation >> 2;
        S1 = (side_generation ^ (S0 << 2)) >> 1;
        S2 = side_generation ^ (S0 << 2) ^ (S1 << 1);
        sides = int[] (S0, S1, S2);

        vec3 tri1_normal;
        vec3 tri2_normal;
        vec3 normal;

        // generate side quads
        for (int i = 0; i < 3; ++i)
        {
            for (int j = 0; j < sides[i]; ++j)
            {

                tri1_normal = cross((pos[i + 1] - pos[i]), (pos[i + 4] - pos[i]));
                tri2_normal = cross((pos[i + 4] - pos[i + 5]), (pos[i + 1] - pos[i + 5]));
                normal = normalize(tri1_normal + tri2_normal);
                eye_normal = normalize(p3d_NormalMatrix * normal);

                gl_Position = proj_pos[i];
                eye_vec = (p3d_ModelViewMatrix * proj_pos[i]).xyz;
                EmitVertex();

                gl_Position = proj_pos[i + 1];
                eye_vec = (p3d_ModelViewMatrix * proj_pos[i + 1]).xyz;
                EmitVertex();

                gl_Position = proj_pos[i + 4];
                eye_vec = (p3d_ModelViewMatrix * proj_pos[i + 4]).xyz;
                EmitVertex();

                gl_Position = proj_pos[i + 5];
                eye_vec = (p3d_ModelViewMatrix * proj_pos[i + 5]).xyz;
                EmitVertex();

                EndPrimitive();

            }
        }

        // Generate internal/bottom triangle

        g_color = vertex[2].color;
        gl_Position = PP2;
        eye_vec = (p3d_ModelViewMatrix * PP2).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[2].normal * -1.);
        EmitVertex();

        g_color = vertex[1].color;
        gl_Position = PP1;
        eye_vec = (p3d_ModelViewMatrix * PP1).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[1].normal * -1.);
        EmitVertex();

        g_color = vertex[0].color;
        gl_Position = PP0;
        eye_vec = (p3d_ModelViewMatrix * PP0).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[0].normal * -1.);
        EmitVertex();

        EndPrimitive();

        // Generate external/top triangle

        g_color = vertex[0].color;
        gl_Position = PP3;
        eye_vec = (p3d_ModelViewMatrix * PP3).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[0].normal);
        EmitVertex();

        g_color = vertex[1].color;
        gl_Position = PP4;
        eye_vec = (p3d_ModelViewMatrix * PP4).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[1].normal);
        EmitVertex();

        g_color = vertex[2].color;
        gl_Position = PP5;
        eye_vec = (p3d_ModelViewMatrix * PP5).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[2].normal);
        EmitVertex();

        EndPrimitive();

    }
"""
