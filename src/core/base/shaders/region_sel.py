# This module contains the shaders used to region-select objects.


# The following vertex shader is used to region-select top-level objects
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

# The following fragment shader is used to determine which objects lie
# within a rectangular region
FRAG_SHADER = """
    #version 420

    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {
        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));
    }
"""

# The following fragment shader is used to constrain the selection to an
# elliptic region
FRAG_SHADER_ELLIPSE = """
    #version 420

    uniform vec4 ellipse_data;
    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {

        float radius, aspect_ratio, offset_x, offset_y, x, y, dist;

        radius = ellipse_data.x;
        aspect_ratio = ellipse_data.y;
        // the ellipse might be clipped by the viewport border, so it is
        // necessary to know the left and bottom offsets of this clipped
        // portion
        offset_x = ellipse_data.z;
        offset_y = ellipse_data.w;
        ivec2 coord = ivec2(gl_FragCoord.xy);
        x = offset_x + coord.x - radius;
        y = (offset_y + coord.y) * aspect_ratio - radius;
        dist = sqrt((x * x) + (y * y));

        // only consider pixels that are inside of the ellipse
        if (dist > radius) {
            discard;
        }

        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));

    }
"""

# The following fragment shader is used to constrain the selection to a
# free-form (point-to-point "fence", lasso or painted) region
FRAG_SHADER_FREE = """
    #version 420

    uniform sampler2D mask_tex;
    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {

        vec4 texelValue = texelFetch(mask_tex, ivec2(gl_FragCoord.xy), 0);

        // discard pixels whose corresponding mask texels are (0., 0., 0., 0.)
        if (texelValue == vec4(0., 0., 0., 0.)) {
            discard;
        }

        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));

    }
"""


# The following fragment shader is used to determine which objects are
# not completely enclosed within a rectangular region
FRAG_SHADER_INV = """
    #version 420

    uniform vec2 buffer_size;
    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {

        int w, h, x, y;

        w = int(buffer_size.x);
        h = int(buffer_size.y);
        x = int(gl_FragCoord.x);
        y = int(gl_FragCoord.y);

        // only consider border pixels
        if ((x > 1) && (x < w) && (y > 1) && (y < h)) {
            discard;
        }

        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));

    }
"""

# The following fragment shader is used to determine which objects are
# not completely enclosed within an elliptic region
FRAG_SHADER_ELLIPSE_INV = """
    #version 420

    uniform vec4 ellipse_data;
    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {

        float radius, aspect_ratio, offset_x, offset_y, x, y, dist;

        radius = ellipse_data.x;
        aspect_ratio = ellipse_data.y;
        // the ellipse might be clipped by the viewport border, so it is
        // necessary to know the left and bottom offsets of this clipped
        // portion
        offset_x = ellipse_data.z;
        offset_y = ellipse_data.w;
        ivec2 coord = ivec2(gl_FragCoord.xy);
        x = offset_x + coord.x - 2 - radius;
        y = (offset_y + coord.y - 2) * aspect_ratio - radius;
        dist = sqrt((x * x) + (y * y));

        // only consider pixels that are outside of the ellipse
        if (dist <= radius) {
            discard;
        }

        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));

    }
"""

# The following fragment shader is used to determine which objects are not
# completely enclosed within a free-form (fence, lasso or painted) region
FRAG_SHADER_FREE_INV = """
    #version 420

    uniform sampler2D mask_tex;
    layout(r32i) uniform iimageBuffer selections;
    flat in int oindex;

    void main() {

        vec4 texelValue = texelFetch(mask_tex, ivec2(gl_FragCoord.xy), 0);

        // only consider pixels whose corresponding mask texels are (0., 0., 0., 0.)
        if (texelValue != vec4(0., 0., 0., 0.)) {
            discard;
        }

        // Write 1 to the location corresponding to the custom index
        imageAtomicOr(selections, (oindex >> 5), 1 << (oindex & 31));

    }
"""


# The following shaders are used to gradually create a mask texture that can
# in turn be used as input for the free-form region-selection fragment shaders.

VERT_SHADER_MASK = """
    #version 420

    uniform mat4 p3d_ModelViewProjectionMatrix;
    in vec4 p3d_Vertex;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    }
"""

FRAG_SHADER_MASK = """
    #version 420

    uniform sampler2D prev_tex;
    uniform vec4 fill_color;
    layout(location = 0) out vec4 out_color;

    void main() {

        vec4 texelValue = texelFetch(prev_tex, ivec2(gl_FragCoord.xy), 0);

        if (texelValue == vec4(0., 0., 0., 0.)) {
            out_color = fill_color;
        }
        else {
            out_color = vec4(0., 0., 0., 0.);
        }

    }
"""
