#version 300 es
precision highp float;

in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

// The panel diagnostic was clean at 250/255, but not at full white.
// Preserve all lower channel values and alpha; only clip the highlights.
void main() {
    vec4 pixel = texture(tex, v_texcoord);
    fragColor = vec4(min(pixel.rgb, vec3(250.0 / 255.0)), pixel.a);
}
