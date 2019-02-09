# This module contains the shaders used to determine interpolated normals to a surface.


VERT_SHADER = """
    #version 330

    uniform mat4 p3d_ModelViewProjectionMatrix;
    in vec4 p3d_Vertex;
    in vec3 p3d_Normal;

    out vec3 normal;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        normal = p3d_Normal;
    }
"""

FRAG_SHADER = """
    #version 330

    in vec3 normal;

    layout(location = 0) out vec4 out_color;

    void main() {
        // output the interpolated normal, in the [0., 1.] range, as a color value
        out_color = vec4(normalize(normal) * .5 + .5, 1.);
    }
"""
