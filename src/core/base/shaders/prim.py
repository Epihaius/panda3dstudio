# This module contains the fragment shader used during the creation of certain geometry primitives.


FRAG_SHADER = """
    #version 150 compatibility

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

    uniform vec4 p3d_Color;
    in vec3 eye_vec;
    in vec3 eye_normal;

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
        f_color = vec4(lightcolor, 1.) * p3d_Color;

    }
"""
