# This module contains the vertex shader used during the creation of cone primitives.


VERT_SHADER = """
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform float bottom_radius;
    uniform float top_radius;
    uniform float height;

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec2 p3d_MultiTexCoord0;
    in vec3 p3d_Normal;

    // Output to fragment shader
    out vec2 texcoord;
    out vec3 eye_vec;
    out vec3 eye_normal;

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

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(pos_new, 1.);
        eye_vec = (p3d_ModelViewMatrix * vec4(pos_new, 1.)).xyz;
        texcoord = p3d_MultiTexCoord0;
        normal_new = p3d_Normal.xyz;

        if (abs(normal_new.z) < epsilon) {
            normal_new *= height_abs;
            up_vec = vec3(0., 0., 1.) * delta_radius;
            normal_new += up_vec;
            normal_new = normalize(normal_new);
        }

        eye_normal = normalize(p3d_NormalMatrix * normal_new);

    }
"""
