# This module contains the vertex shaders used during the creation of torus primitives.


main_computation = """
        vec3 pos_old;
        vec3 pos_new;
        vec3 pos_vec;
        vec3 section_center;
        float d;
        // original ring radius: 2.
        // original cross section radius: 1.
        pos_old = p3d_Vertex.xyz;
        // compute the horizontal distance to the vertex from the torus center
        d = sqrt(pos_old.x * pos_old.x + pos_old.y * pos_old.y);
        d = 2. / max(.0001, d);
        // compute the center of the cross section to which the vertex belongs
        section_center = vec3(pos_old.x * d, pos_old.y * d, 0.);
        pos_vec = pos_old - section_center;
        // the length of pos_vec should be 1. (the original cross section radius),
        // so it can be multiplied by the new cross section radius without prior
        // normalization
        pos_vec *= section_radius;
        // compute the new section center, keeping in mind that the original ring
        // radius equals 2.
        section_center *= .5 * ring_radius;
        // get the new vertex position by adding the updated pos_vec to the new
        // cross section center
        pos_new = section_center + pos_vec;
"""


VERT_SHADER = ("""
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform float ring_radius;
    uniform float section_radius;

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

"""
+
main_computation
+
"""

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(pos_new, 1.);
        eye_vec = (p3d_ModelViewMatrix * vec4(pos_new, 1.)).xyz;
        texcoord = p3d_MultiTexCoord0;
        eye_normal = normalize(p3d_NormalMatrix * p3d_Normal);

    }
""")


VERT_SHADER_WIRE = ("""
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelMatrix;
    uniform float ring_radius;
    uniform float section_radius;

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

"""
+
main_computation
+
"""

        gl_Position = p3d_ModelMatrix * vec4(pos_new, 1.);
        vertex.color = p3d_Color;
        vertex.side_gen = sides;

    }
""")
