# This module contains the shaders used for rendering the grid.


VERT_SHADER = """
    #version 330

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;

    out Vertex
    {
        vec3 pos_model_space;
        vec3 pos_cam_space;
        vec4 color;
    } vertex;

    void main()
    {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        vertex.pos_model_space = p3d_Vertex.xyz;
        vertex.pos_cam_space = (p3d_ModelViewMatrix * p3d_Vertex).xyz;
        vertex.color = p3d_Color;
    }
"""

GEOM_SHADER = """
    #version 330

    layout(lines) in;

    // One line will be generated: 2 vertices
    layout(line_strip, max_vertices=2) out;

    uniform vec3 offset;
    uniform vec3 plane_normal;

    in Vertex
    {
        vec3 pos_model_space;
        vec3 pos_cam_space;
        vec4 color;
    } vertex[];

    out vec3 grid_point;
    out vec4 vertex_color;

    void main()
    {

        vec3 P0 = vertex[0].pos_model_space + offset;
        vec3 P1 = vertex[1].pos_model_space + offset;
        vertex_color = vertex[0].color;
        float epsilon = .0001;

        // render the main axis lines in pure red, green or blue;
        // this is determined by their end point coordinates and
        // the normal of the currently active grid plane
        if (plane_normal.z == 1.) {  // XY-plane
            if (abs(P0.y) < epsilon && abs(P1.y) < epsilon)  // X-axis
                vertex_color = vec4(1., 0., 0., 1.);
            else if (abs(P0.x) < epsilon && abs(P1.x) < epsilon)  // Y-axis
                vertex_color = vec4(0., 1., 0., 1.);
        }
        else if (plane_normal.y == 1.) {  // XZ-plane
            if (abs(P0.z) < epsilon && abs(P1.z) < epsilon)  // X-axis
                vertex_color = vec4(1., 0., 0., 1.);
            else if (abs(P0.x) < epsilon && abs(P1.x) < epsilon)  // Z-axis
                vertex_color = vec4(0., 0., 1., 1.);
        }
        else if (plane_normal.x == 1.) {  // YZ-plane
            if (abs(P0.z) < epsilon && abs(P1.z) < epsilon)  // Y-axis
                vertex_color = vec4(0., 1., 0., 1.);
            else if (abs(P0.y) < epsilon && abs(P1.y) < epsilon)  // Z-axis
                vertex_color = vec4(0., 0., 1., 1.);
        }

        gl_Position = gl_in[0].gl_Position;
        grid_point = vertex[0].pos_cam_space;

        EmitVertex();

        gl_Position = gl_in[1].gl_Position;
        grid_point = vertex[1].pos_cam_space;

        EmitVertex();

        EndPrimitive();

    }
"""

FRAG_SHADER = """
    #version 330

    uniform mat4 p3d_ModelViewMatrix;
    uniform mat4 p3d_ProjectionMatrix;
    uniform vec3 plane_normal;

    in vec3 grid_point;
    in vec4 vertex_color;

    layout(location = 0) out vec4 out_color;

    void main()
    {

        vec3 normal_cam_space;

        // get plane normal in camera space
        normal_cam_space = (p3d_ModelViewMatrix * vec4(plane_normal.xyz, 1.)).xyz;
        // translation should not be applied to a vector
        normal_cam_space -= (p3d_ModelViewMatrix * vec4(0., 0., 0., 1.)).xyz;
        // normalize plane normal
        normal_cam_space = normalize(normal_cam_space);
        out_color = vertex_color;

        if (p3d_ProjectionMatrix[3].w == 1.) {
            // orthographic lens;
            // compute transparency based on angle between plane normal and forward camera vector
            out_color.w = min(1., max(0., abs(dot(normal_cam_space, vec3(0., 0., -1.))) - .5) * 4.);
        }
        else {
            // perspective lens;
            // compute projection of camera origin (0., 0., 0.) onto grid plane
            vec3 orig_proj = normal_cam_space * dot(grid_point, normal_cam_space);
            // compute projection of forward camera vector onto grid plane
            vec3 v = grid_point - vec3(0., 0., -1.);
            float dist;
            dist = dot(v, normal_cam_space);
            vec3 forward_point_proj = vec3(0., 0., -1.) + normal_cam_space * dist;
            vec3 vec_proj = normalize(forward_point_proj - orig_proj);
            // project grid point onto projection of forward camera vector
            vec3 grid_point_proj = orig_proj + vec_proj * dot((grid_point - orig_proj), vec_proj);
            // compute transparency falloff based on angle between camera origin projection vector
            // and projected grid point vector
            float falloff = dot(normalize(orig_proj), normalize(grid_point_proj));
            out_color.w = 10. * falloff - 3.;
        }

    }
"""
