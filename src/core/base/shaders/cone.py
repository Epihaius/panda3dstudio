# This module contains the shaders used during the creation of cone primitives.


VERT_SHADER = """
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelViewMatrix;
    uniform float bottom_radius;
    uniform float top_radius;
    uniform float height;

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in vec2 p3d_MultiTexCoord0;
    in vec3 p3d_Normal;

    out Vertex
    {
        vec4 color;
        vec2 texcoord;
        vec3 normal;
        vec3 eye_vec;
        float height_abs;
        float delta_radius;
        float epsilon;
    } vertex;

    void main(void)
    {

        vec3 pos_old;
        vec3 pos_new;
        float height_abs;
        float z;
        float delta_radius;
        float epsilon;
        float new_dist;
        float radius;
        float h;

        // original radii: 1.
        // original height: 1.
        pos_old = p3d_Vertex.xyz;
        height_abs = abs(height);
        z = pos_old.z * height_abs;

        if (height < 0.) {
            z -= height_abs;
            delta_radius = top_radius - bottom_radius;
        }
        else {
            delta_radius = bottom_radius - top_radius;
        }

        epsilon = 1.e-010;

        if (abs(delta_radius) < epsilon) {

            new_dist = bottom_radius;

        }
        else {

            if (abs(bottom_radius) >= epsilon) {
                radius = bottom_radius;
            }
            else {
                radius = top_radius;
            }

            h = height_abs * radius / delta_radius;
            new_dist = (h - z) * radius / h;

        }

        pos_new = p3d_Vertex.xyz;
        pos_new.z = 0.;
        pos_new *= new_dist;
        pos_new.z = z;

        gl_Position = vec4(pos_new, 1.);
        vertex.texcoord = p3d_MultiTexCoord0;
        vertex.normal = p3d_Normal.xyz;
        vertex.eye_vec = (p3d_ModelViewMatrix * vec4(pos_new, 1.)).xyz;
        vertex.height_abs = height_abs;
        vertex.delta_radius = delta_radius;
        vertex.epsilon = epsilon;

    }
"""

GEOM_SHADER = """
    #version 330

    layout(triangles) in;

    // One triangle will be generated: 3 vertices
    layout(triangle_strip, max_vertices=3) out;

    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform bool smooth_normals;

    in Vertex
    {
        vec4 color;
        vec2 texcoord;
        vec3 normal;
        vec3 eye_vec;
        float height_abs;
        float delta_radius;
        float epsilon;
    } vertex[];

    // Output to fragment shader
    out vec4 vertex_color;
    out vec2 texcoord;
    out vec3 eye_vec;
    out vec3 eye_normal;

    void main()
    {

        float height_abs = vertex[0].height_abs;
        float delta_radius = vertex[0].delta_radius;
        float epsilon = vertex[0].epsilon;
        vec3 P0, P1, P2, V0, V1, normal_new;
        vec3 face_normal = vec3(0., 0., 0.);

        if (smooth_normals == false)
        {
            P0 = gl_in[0].gl_Position.xyz;
            P1 = gl_in[1].gl_Position.xyz;
            P2 = gl_in[2].gl_Position.xyz;
            V0 = P1 - P0;
            V1 = P2 - P1;
            face_normal = cross(V0, V1);
        }

        for (int i = 0; i < 3; ++i)
        {

            gl_Position = p3d_ModelViewProjectionMatrix * gl_in[i].gl_Position;
            vertex_color = vertex[i].color;
            texcoord = vertex[i].texcoord;
            eye_vec = vertex[i].eye_vec;

            if (smooth_normals)
            {
                normal_new = vertex[i].normal.xyz;

                if (abs(normal_new.z) < epsilon) {
                    normal_new *= height_abs;
                    normal_new.z += delta_radius;
                    normal_new = normalize(normal_new);
                }
            }
            else {
                normal_new = face_normal;
            }

            eye_normal = normalize(p3d_NormalMatrix * normal_new);

            EmitVertex();

        }

        EndPrimitive();

    }
"""


VERT_SHADER_WIRE = """
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelMatrix;
    uniform float bottom_radius;
    uniform float top_radius;
    uniform float height;

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in int sides;

    out Vertex
    {
        vec4 color;
        int side_gen;
    } vertex;

    void main(void)
    {

        vec3 pos_old;
        vec3 pos_new;
        vec3 normal_new;
        vec3 up_vec;
        float height_abs;
        float z;
        float delta_radius;
        float epsilon;
        float new_dist;
        float radius;
        float h;

        // original radii: 1.
        // original height: 1.
        pos_old = p3d_Vertex.xyz;
        height_abs = abs(height);
        z = pos_old.z * height_abs;

        if (height < 0.) {
            z -= height_abs;
            delta_radius = top_radius - bottom_radius;
        }
        else {
            delta_radius = bottom_radius - top_radius;
        }

        epsilon = 1.e-010;

        if (abs(delta_radius) < epsilon) {

            new_dist = bottom_radius;

        }
        else {

            if (abs(bottom_radius) >= epsilon) {
                radius = bottom_radius;
            }
            else {
                radius = top_radius;
            }

            h = height_abs * radius / delta_radius;
            new_dist = (h - z) * radius / h;

        }

        pos_new = p3d_Vertex.xyz;
        pos_new.z = 0.;
        pos_new *= new_dist;
        pos_new.z = z;

        gl_Position = p3d_ModelMatrix * vec4(pos_new, 1.);
        vertex.color = p3d_Color;
        vertex.side_gen = sides;

    }
"""
