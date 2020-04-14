# This module contains the shaders used to preview polygon extrusions and insets.


VERT_SHADER = """
    #version 330

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec3 p3d_Normal;
    in vec4 p3d_Color;
    in vec3 averaged_normal;
    in ivec2 sides;
    in vec3 extrusion1_vec;
    in vec3 extrusion2_vec;
    in vec3 extrusion3_vec;
    in vec4 inset1_vec;
    in vec4 inset2_vec;

    out Vertex
    {
        vec3 normal;
        vec4 color;
        int side_gen[2];
        vec3 extr_vecs[6];
        vec4 inset_vecs[2];
    } vertex;

    void main()
    {
        gl_Position = p3d_Vertex;
        vertex.normal = p3d_Normal;
        vertex.color = p3d_Color;
        vertex.side_gen = int[] (sides.x, sides.y);
        vertex.extr_vecs = vec3[] (extrusion1_vec, extrusion2_vec, extrusion3_vec,
                                   extrusion2_vec, averaged_normal, p3d_Normal);
        vertex.inset_vecs = vec4[] (inset1_vec, inset2_vec);
    }
"""

GEOM_SHADER = """
    #version 330

    layout(triangles) in;

    // One top triangle and a maximum of three side quads will be generated: 15 vertices
    layout(triangle_strip, max_vertices=15) out;

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat3 p3d_NormalMatrix;
    uniform float extrusion;
    uniform float inset;
    uniform int extr_inset_type;

    in Vertex
    {
        vec3 normal;
        vec4 color;
        int side_gen[2];
        vec3 extr_vecs[6];
        vec4 inset_vecs[2];
    } vertex[];

    out vec4 g_color;
    out vec3 eye_vec;
    out vec3 eye_normal;

    void main()
    {

        g_color = vertex[0].color;

        vec3 extr_vec;
        vec4 inset_vec;

        vec3 P0 = gl_in[0].gl_Position.xyz;
        vec3 P1 = gl_in[1].gl_Position.xyz;
        vec3 P2 = gl_in[2].gl_Position.xyz;
        extr_vec = vertex[0].extr_vecs[extr_inset_type];
        inset_vec = vertex[0].inset_vecs[extr_inset_type % 2];
        vec3 P3 = P0 + extr_vec * extrusion + inset_vec.xyz * inset_vec.w * inset;
        extr_vec = vertex[1].extr_vecs[extr_inset_type];
        inset_vec = vertex[1].inset_vecs[extr_inset_type % 2];
        vec3 P4 = P1 + extr_vec * extrusion + inset_vec.xyz * inset_vec.w * inset;
        extr_vec = vertex[2].extr_vecs[extr_inset_type];
        inset_vec = vertex[2].inset_vecs[extr_inset_type % 2];
        vec3 P5 = P2 + extr_vec * extrusion + inset_vec.xyz * inset_vec.w * inset;
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
        side_generation = vertex[0].side_gen[extr_inset_type % 2];
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

        // Generate top triangle

        g_color = vec4(1., 0., 0., 1.);

        gl_Position = PP3;
        eye_vec = (p3d_ModelViewMatrix * PP3).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[0].normal);
        EmitVertex();

        gl_Position = PP4;
        eye_vec = (p3d_ModelViewMatrix * PP4).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[1].normal);
        EmitVertex();

        gl_Position = PP5;
        eye_vec = (p3d_ModelViewMatrix * PP5).xyz;
        eye_normal = normalize(p3d_NormalMatrix * vertex[2].normal);
        EmitVertex();

        EndPrimitive();

    }
"""


FRAG_SHADER = """
    #version 150 compatibility

    uniform sampler2D p3d_Texture0;
    uniform struct PandaMaterial {
        vec4 ambient;
        vec4 diffuse;
        vec4 emission;
        vec3 specular;
        float shininess;
    } p3d_Material;

    uniform struct {
        vec4 ambient;
    } p3d_LightModel;

    in vec2 texcoord;
    in vec3 eye_vec;
    in vec3 eye_normal;
    in vec4 g_color;

    out vec4 f_color;

    #define MAX_LIGHTS 1 // to be modified when needed

    // https://en.wikibooks.org/wiki/GLSL_Programming/Blender/Diffuse_Reflection

    void main() {

        vec3 EyeDir = normalize(-eye_vec); // we are in Eye Coordinates, so EyePos is (0., 0., 0.)
        float attenuation;

        // Lights
        vec3 lightcolor = vec3(0., 0., 0.);

        // Ambient
        lightcolor += vec3(p3d_LightModel.ambient * p3d_Material.ambient);

        // Emission
        lightcolor += vec3(p3d_Material.emission);

        for (int lm=0; lm<MAX_LIGHTS; lm++)
        {

            vec3 LightDir = vec3(0., 0., 0.);

            if (gl_LightSource[lm].position.w == 0.) // Directional light?
            {
                LightDir = normalize(vec3(gl_LightSource[lm].position.xyz));
                attenuation = 1.; // no attenuation with Dir Light
            }
            else // point or spot light?
            {
                LightDir = normalize(gl_LightSource[lm].position.xyz - eye_vec);
                // Diffuse and Specular Attenuation for point and spotlight
                attenuation = 1. / (gl_LightSource[lm].constantAttenuation
                                    + gl_LightSource[lm].linearAttenuation * length(LightDir)
                                    + gl_LightSource[lm].quadraticAttenuation
                                        * length(LightDir) * length(LightDir));
                if (gl_LightSource[lm].spotCutoff <= 90.) // spotlight?
                {
                    float clampedCosine = max(0., dot(-LightDir, gl_LightSource[lm].spotDirection));
                    if (clampedCosine < gl_LightSource[lm].spotCosCutoff)
                    // outside of spotlight cone?
                    {
                        attenuation = 0.;
                    }
                    else
                    {
                        attenuation = attenuation * pow(clampedCosine, gl_LightSource[lm].spotExponent);
                    }
                }
            }

            vec3 ReflectDir = normalize(-reflect(LightDir, eye_normal));

            // Diffuse
            float NdotL = dot(normalize(eye_normal), LightDir);
            vec3 diffuseandspec = clamp(p3d_Material.diffuse.rgb * gl_LightSource[lm].diffuse.rgb
                                        * NdotL, 0., 1.);

            // Specular
            vec4 specular = vec4(p3d_Material.specular, 1) * gl_LightSource[lm].specular
                            * pow(max(dot(ReflectDir, EyeDir), 0), p3d_Material.shininess);
            specular = clamp(specular, 0., 1.);
            diffuseandspec += specular.xyz;

            diffuseandspec *= attenuation;
            diffuseandspec = clamp(diffuseandspec, 0., 1.);
            lightcolor += diffuseandspec;
        }

        // Final Color
        f_color = vec4(lightcolor, 1.) * g_color * texture(p3d_Texture0, texcoord);

    }
"""
