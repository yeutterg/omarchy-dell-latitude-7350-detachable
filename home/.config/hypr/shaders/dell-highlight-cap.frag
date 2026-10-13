#version 300 es
precision highp float;

in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

// Partial mitigation: removing the 240/255 cap made the artifact much worse.
// Preserve lower channel values and alpha; only clip the highlights.
void main() {
    vec4 pixel = texture(tex, v_texcoord);
    fragColor = vec4(min(pixel.rgb, vec3(240.0 / 255.0)), pixel.a);
}
