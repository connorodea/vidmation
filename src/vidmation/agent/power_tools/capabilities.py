"""Tool definitions for CLI capabilities.

Each tool is defined with:
- name: Tool identifier
- description: What it does (detailed enough for Claude to generate correct syntax)
- input_schema: JSON Schema for parameters
- examples: Example commands (helps Claude generate correct syntax)

These definitions are passed to the Anthropic API as tool schemas so that
Claude can call them during the agent loop.
"""

from __future__ import annotations

# ======================================================================
# SHELL EXECUTION (generic)
# ======================================================================

SHELL_TOOLS: list[dict] = [
    {
        "name": "run_shell_command",
        "description": (
            "Execute an arbitrary shell command in the sandboxed work directory. "
            "Use this for one-off commands or chaining multiple tools with pipes. "
            "All file paths must be relative to the work directory. "
            "Blocked commands: rm, sudo, curl, wget, ssh, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this command does.",
                },
            },
            "required": ["command"],
        },
    },
]

# ======================================================================
# IMAGEMAGICK TOOLS
# ======================================================================

IMAGEMAGICK_TOOLS: list[dict] = [
    # --- COMPOSITING ---
    {
        "name": "imagemagick_composite",
        "description": (
            "Composite/overlay images together. Supports blend modes, positioning, "
            "and opacity. Use this for layering images, watermarks, overlays.\n\n"
            "Example: magick base.png overlay.png -gravity center -compose over -composite output.png\n"
            "Example with opacity: magick base.png \\( overlay.png -alpha set -channel A -evaluate multiply 0.5 +channel \\) "
            "-gravity center -compose over -composite output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "base_image": {
                    "type": "string",
                    "description": "Path to the base/background image (relative to work dir).",
                },
                "overlay_image": {
                    "type": "string",
                    "description": "Path to the overlay/foreground image.",
                },
                "output": {
                    "type": "string",
                    "description": "Output file path.",
                },
                "geometry": {
                    "type": "string",
                    "description": "Position offset, e.g. '+100+50' or '+0+0'.",
                    "default": "+0+0",
                },
                "gravity": {
                    "type": "string",
                    "enum": [
                        "NorthWest", "North", "NorthEast",
                        "West", "Center", "East",
                        "SouthWest", "South", "SouthEast",
                    ],
                    "description": "Gravity anchor for overlay positioning.",
                    "default": "NorthWest",
                },
                "compose": {
                    "type": "string",
                    "enum": [
                        "over", "multiply", "screen", "dissolve", "hardlight",
                        "softlight", "overlay", "difference", "addition",
                        "darken", "lighten", "colordodge", "colorburn",
                    ],
                    "description": "Blend/compose mode.",
                    "default": "over",
                },
                "opacity": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Overlay opacity percentage (100 = fully opaque).",
                    "default": 100,
                },
            },
            "required": ["base_image", "overlay_image", "output"],
        },
    },
    # --- TEXT RENDERING ---
    {
        "name": "imagemagick_text",
        "description": (
            "Render text onto an image with custom fonts, colors, sizes, and effects. "
            "This is the primary tool for adding text to images.\n\n"
            "Example: magick input.png -gravity South -font Arial-Bold -pointsize 72 "
            "-fill white -stroke black -strokewidth 2 -annotate +0+30 'Hello World' output.png\n\n"
            "For text with a shadow: magick input.png "
            "\\( -clone 0 -gravity South -font Arial-Bold -pointsize 72 "
            "-fill black -annotate +2+28 'Hello World' -blur 0x3 \\) "
            "-gravity South -font Arial-Bold -pointsize 72 "
            "-fill white -annotate +0+30 'Hello World' output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output": {
                    "type": "string",
                    "description": "Output file path.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to render.",
                },
                "font": {
                    "type": "string",
                    "description": "Font name or path to .ttf/.otf file.",
                    "default": "Arial-Bold",
                },
                "pointsize": {
                    "type": "integer",
                    "description": "Font size in points.",
                    "default": 48,
                },
                "fill_color": {
                    "type": "string",
                    "description": "Text fill color (name, hex like '#FF0000', or rgba).",
                    "default": "white",
                },
                "stroke_color": {
                    "type": "string",
                    "description": "Text outline/stroke color. Empty string for no stroke.",
                    "default": "",
                },
                "stroke_width": {
                    "type": "number",
                    "description": "Stroke width in pixels.",
                    "default": 0,
                },
                "gravity": {
                    "type": "string",
                    "enum": [
                        "NorthWest", "North", "NorthEast",
                        "West", "Center", "East",
                        "SouthWest", "South", "SouthEast",
                    ],
                    "default": "Center",
                },
                "geometry": {
                    "type": "string",
                    "description": "Position offset from gravity anchor, e.g. '+0+30'.",
                    "default": "+0+0",
                },
                "shadow": {
                    "type": "boolean",
                    "description": "Add a drop shadow behind the text.",
                    "default": False,
                },
                "shadow_color": {
                    "type": "string",
                    "description": "Shadow color.",
                    "default": "black",
                },
                "shadow_offset": {
                    "type": "string",
                    "description": "Shadow offset, e.g. '+2+2'.",
                    "default": "+2+2",
                },
                "shadow_blur": {
                    "type": "number",
                    "description": "Shadow blur sigma.",
                    "default": 3,
                },
            },
            "required": ["input_image", "output", "text"],
        },
    },
    # --- ANNOTATE ---
    {
        "name": "imagemagick_annotate",
        "description": (
            "Add text annotations with precise positioning, rotation, and gravity. "
            "Unlike imagemagick_text, this gives more control over rotation angle.\n\n"
            "Example: magick input.png -gravity NorthEast -font Helvetica -pointsize 24 "
            "-fill 'rgba(255,255,255,0.7)' -annotate +20+20 'Watermark' output.png\n"
            "With rotation: magick input.png -font Courier -pointsize 36 "
            "-fill gray -annotate 45x45+100+200 'DRAFT' output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string", "description": "Input image path."},
                "output": {"type": "string", "description": "Output file path."},
                "text": {"type": "string", "description": "Annotation text."},
                "font": {"type": "string", "default": "Helvetica"},
                "pointsize": {"type": "integer", "default": 24},
                "fill_color": {"type": "string", "default": "white"},
                "gravity": {
                    "type": "string",
                    "default": "NorthWest",
                    "enum": [
                        "NorthWest", "North", "NorthEast",
                        "West", "Center", "East",
                        "SouthWest", "South", "SouthEast",
                    ],
                },
                "rotation": {
                    "type": "number",
                    "description": "Rotation angle in degrees.",
                    "default": 0,
                },
                "geometry": {"type": "string", "default": "+0+0"},
            },
            "required": ["input_image", "output", "text"],
        },
    },
    # --- CAPTION (auto-wrapping text) ---
    {
        "name": "imagemagick_caption",
        "description": (
            "Render auto-wrapping text that fits within specified dimensions. "
            "Great for long text that needs to wrap within a bounding box.\n\n"
            "Example: magick -size 600x200 -background none -fill white "
            "-font Arial -gravity Center caption:'This is a long piece of text "
            "that will automatically wrap to fit within the given width' text.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to render (will auto-wrap)."},
                "output": {"type": "string", "description": "Output file path."},
                "width": {"type": "integer", "description": "Maximum width in pixels.", "default": 800},
                "height": {"type": "integer", "description": "Maximum height in pixels.", "default": 200},
                "font": {"type": "string", "default": "Arial"},
                "pointsize": {"type": "integer", "description": "Font size (0 = auto-size to fit).", "default": 0},
                "fill_color": {"type": "string", "default": "white"},
                "background": {"type": "string", "description": "Background color ('none' for transparent).", "default": "none"},
                "gravity": {"type": "string", "default": "Center"},
            },
            "required": ["text", "output"],
        },
    },
    # --- LABEL (single-line text) ---
    {
        "name": "imagemagick_label",
        "description": (
            "Render a single line of text, auto-sized to fit. Does not wrap.\n\n"
            "Example: magick -background none -fill white -font Impact "
            "-pointsize 96 label:'SUBSCRIBE' label.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Single line of text."},
                "output": {"type": "string", "description": "Output file path."},
                "font": {"type": "string", "default": "Impact"},
                "pointsize": {"type": "integer", "default": 72},
                "fill_color": {"type": "string", "default": "white"},
                "background": {"type": "string", "default": "none"},
            },
            "required": ["text", "output"],
        },
    },
    # --- EFFECTS ---
    {
        "name": "imagemagick_blur",
        "description": (
            "Apply blur effects to an image: Gaussian, motion, or radial.\n\n"
            "Gaussian: magick input.png -blur 0x8 output.png\n"
            "Motion: magick input.png -motion-blur 0x12+45 output.png  (angle=45 deg)\n"
            "Radial: magick input.png -radial-blur 10 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["gaussian", "motion", "radial"],
                    "default": "gaussian",
                },
                "radius": {"type": "number", "description": "Blur radius.", "default": 0},
                "sigma": {"type": "number", "description": "Blur sigma (strength).", "default": 8},
                "angle": {"type": "number", "description": "Angle for motion blur (degrees).", "default": 0},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_sharpen",
        "description": (
            "Sharpen an image using Gaussian sharpen or unsharp mask.\n\n"
            "Sharpen: magick input.png -sharpen 0x2 output.png\n"
            "Unsharp: magick input.png -unsharp 0x5+1.5+0.02 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "type": {"type": "string", "enum": ["sharpen", "unsharp"], "default": "unsharp"},
                "radius": {"type": "number", "default": 0},
                "sigma": {"type": "number", "default": 5},
                "amount": {"type": "number", "description": "Unsharp mask gain.", "default": 1.5},
                "threshold": {"type": "number", "description": "Unsharp mask threshold.", "default": 0.02},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_shadow",
        "description": (
            "Add a drop shadow or glow effect around an image element.\n\n"
            "Example: magick input.png \\( +clone -background black -shadow 60x5+5+5 \\) "
            "+swap -background none -layers merge +repage output.png\n"
            "Glow: magick input.png \\( +clone -background '#00FFFF' -shadow 100x10+0+0 \\) "
            "+swap -background none -layers merge +repage output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "color": {"type": "string", "description": "Shadow color.", "default": "black"},
                "opacity": {"type": "number", "description": "Shadow opacity percent.", "default": 60},
                "sigma": {"type": "number", "description": "Shadow blur sigma.", "default": 5},
                "x_offset": {"type": "integer", "description": "Horizontal offset.", "default": 5},
                "y_offset": {"type": "integer", "description": "Vertical offset.", "default": 5},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_border",
        "description": (
            "Add borders, frames, or rounded corners to an image.\n\n"
            "Border: magick input.png -bordercolor '#FF0000' -border 10 output.png\n"
            "Rounded: magick input.png \\( +clone -alpha extract "
            "-draw 'fill black polygon 0,0 0,15 15,0 fill white circle 15,15 15,0' "
            "\\( +clone -flip \\) -compose Multiply -composite "
            "\\( +clone -flop \\) -compose Multiply -composite \\) "
            "-alpha off -compose CopyOpacity -composite output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "type": {"type": "string", "enum": ["solid", "rounded", "frame"], "default": "solid"},
                "width": {"type": "integer", "description": "Border width in pixels.", "default": 10},
                "color": {"type": "string", "default": "white"},
                "corner_radius": {"type": "integer", "description": "Corner radius for rounded type.", "default": 20},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_gradient",
        "description": (
            "Create a gradient image (linear or radial).\n\n"
            "Linear: magick -size 1920x1080 gradient:'#1a1a2e'-'#16213e' gradient.png\n"
            "Radial: magick -size 1920x1080 radial-gradient:'#e94560'-'#0f3460' gradient.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output": {"type": "string"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
                "type": {"type": "string", "enum": ["linear", "radial"], "default": "linear"},
                "color_start": {"type": "string", "description": "Start color.", "default": "#1a1a2e"},
                "color_end": {"type": "string", "description": "End color.", "default": "#16213e"},
            },
            "required": ["output"],
        },
    },
    {
        "name": "imagemagick_vignette",
        "description": (
            "Apply a vignette (edge darkening) effect.\n\n"
            "Example: magick input.png -vignette 0x40 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "radius": {"type": "number", "default": 0},
                "sigma": {"type": "number", "description": "Vignette spread.", "default": 40},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_colorize",
        "description": (
            "Color tinting, sepia, or duotone effects.\n\n"
            "Sepia: magick input.png -sepia-tone 80% output.png\n"
            "Tint: magick input.png -fill '#e94560' -colorize 30% output.png\n"
            "Duotone: magick input.png -grayscale Rec709Luminance "
            "-fill '#1a1a2e' -colorize 100% \\( input.png -grayscale Rec709Luminance "
            "-fill '#e94560' -colorize 100% \\) -compose screen -composite output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "type": {"type": "string", "enum": ["tint", "sepia", "duotone", "grayscale"], "default": "tint"},
                "color": {"type": "string", "description": "Tint color for 'tint' mode.", "default": "#e94560"},
                "amount": {"type": "number", "description": "Tint amount percentage (0-100).", "default": 30},
                "sepia_threshold": {"type": "number", "description": "Sepia tone threshold percent.", "default": 80},
                "duotone_shadow": {"type": "string", "description": "Shadow color for duotone.", "default": "#1a1a2e"},
                "duotone_highlight": {"type": "string", "description": "Highlight color for duotone.", "default": "#e94560"},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_brightness_contrast",
        "description": (
            "Adjust brightness, contrast, and gamma of an image.\n\n"
            "Brightness/Contrast: magick input.png -brightness-contrast 10x20 output.png\n"
            "Gamma: magick input.png -gamma 1.2 output.png\n"
            "Levels: magick input.png -level 10%,90%,1.2 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "brightness": {"type": "integer", "description": "Brightness adjustment (-100 to 100).", "default": 0},
                "contrast": {"type": "integer", "description": "Contrast adjustment (-100 to 100).", "default": 0},
                "gamma": {"type": "number", "description": "Gamma correction (1.0 = no change).", "default": 1.0},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_hue_saturation",
        "description": (
            "Adjust hue, saturation, and lightness (HSL color grading).\n\n"
            "Example: magick input.png -modulate 100,130,100 output.png\n"
            "Args are: brightness%,saturation%,hue%  (100 = no change)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "hue": {"type": "number", "description": "Hue rotation percent (100 = no change, 0-200).", "default": 100},
                "saturation": {"type": "number", "description": "Saturation percent (100 = no change).", "default": 100},
                "lightness": {"type": "number", "description": "Lightness percent (100 = no change).", "default": 100},
            },
            "required": ["input_image", "output"],
        },
    },
    # --- TRANSFORMS ---
    {
        "name": "imagemagick_resize",
        "description": (
            "Resize an image with various algorithms.\n\n"
            "Fit within bounds: magick input.png -resize 1280x720 output.png\n"
            "Force exact size: magick input.png -resize 1280x720! output.png\n"
            "Fill & crop: magick input.png -resize 1280x720^ -gravity center -extent 1280x720 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "mode": {
                    "type": "string",
                    "enum": ["fit", "fill", "exact", "shrink_only"],
                    "description": (
                        "fit: Scale to fit within bounds (aspect preserved). "
                        "fill: Scale to fill bounds, then crop to exact size. "
                        "exact: Force exact dimensions (may distort). "
                        "shrink_only: Only shrink, never enlarge."
                    ),
                    "default": "fit",
                },
                "filter": {
                    "type": "string",
                    "enum": ["Lanczos", "Mitchell", "Catrom", "Point", "Box"],
                    "description": "Resize filter algorithm.",
                    "default": "Lanczos",
                },
            },
            "required": ["input_image", "output", "width", "height"],
        },
    },
    {
        "name": "imagemagick_crop",
        "description": (
            "Crop an image region.\n\n"
            "By geometry: magick input.png -crop 800x600+100+50 +repage output.png\n"
            "With gravity: magick input.png -gravity Center -crop 800x600+0+0 +repage output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "width": {"type": "integer", "description": "Crop width."},
                "height": {"type": "integer", "description": "Crop height."},
                "x_offset": {"type": "integer", "description": "X offset from gravity.", "default": 0},
                "y_offset": {"type": "integer", "description": "Y offset from gravity.", "default": 0},
                "gravity": {"type": "string", "default": "NorthWest"},
            },
            "required": ["input_image", "output", "width", "height"],
        },
    },
    {
        "name": "imagemagick_rotate",
        "description": (
            "Rotate an image by an arbitrary angle.\n\n"
            "Example: magick input.png -background none -rotate 15 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "angle": {"type": "number", "description": "Rotation angle in degrees."},
                "background": {"type": "string", "description": "Background color for exposed areas.", "default": "none"},
            },
            "required": ["input_image", "output", "angle"],
        },
    },
    {
        "name": "imagemagick_flip",
        "description": (
            "Flip an image horizontally (flop) or vertically (flip).\n\n"
            "Horizontal: magick input.png -flop output.png\n"
            "Vertical: magick input.png -flip output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "direction": {"type": "string", "enum": ["horizontal", "vertical"], "default": "horizontal"},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_distort",
        "description": (
            "Apply perspective, barrel, arc, or other distortion effects.\n\n"
            "Perspective: magick input.png -distort Perspective "
            "'0,0 50,10  800,0 750,20  0,600 30,580  800,600 770,590' output.png\n"
            "Barrel: magick input.png -distort Barrel '0.1 0 0 1.0' output.png\n"
            "Arc: magick input.png -distort Arc 180 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["perspective", "barrel", "arc", "polar", "depolar"],
                    "default": "perspective",
                },
                "parameters": {
                    "type": "string",
                    "description": "Distortion parameters (tool-specific format).",
                },
                "background": {"type": "string", "default": "none"},
            },
            "required": ["input_image", "output", "type", "parameters"],
        },
    },
    # --- COMPOSITION ---
    {
        "name": "imagemagick_montage",
        "description": (
            "Create image grids/collages from multiple images.\n\n"
            "Example: magick montage img1.png img2.png img3.png img4.png "
            "-tile 2x2 -geometry 640x360+5+5 -background '#1a1a2e' collage.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of input image paths.",
                },
                "output": {"type": "string"},
                "tile": {"type": "string", "description": "Grid layout, e.g. '2x2', '3x3', '4x'.", "default": "2x2"},
                "geometry": {"type": "string", "description": "Tile size + padding, e.g. '640x360+5+5'.", "default": "640x360+5+5"},
                "background": {"type": "string", "default": "#1a1a2e"},
            },
            "required": ["images", "output"],
        },
    },
    {
        "name": "imagemagick_append",
        "description": (
            "Stack images horizontally or vertically.\n\n"
            "Horizontal: magick img1.png img2.png +append output.png\n"
            "Vertical: magick img1.png img2.png -append output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of images to stack.",
                },
                "output": {"type": "string"},
                "direction": {"type": "string", "enum": ["horizontal", "vertical"], "default": "horizontal"},
            },
            "required": ["images", "output"],
        },
    },
    {
        "name": "imagemagick_mask",
        "description": (
            "Apply an alpha mask to an image.\n\n"
            "Example: magick input.png mask.png -alpha Off -compose CopyOpacity -composite output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string", "description": "Image to mask."},
                "mask_image": {"type": "string", "description": "Grayscale mask (white=opaque, black=transparent)."},
                "output": {"type": "string"},
            },
            "required": ["input_image", "mask_image", "output"],
        },
    },
    # --- FORMAT & OPTIMIZATION ---
    {
        "name": "imagemagick_convert",
        "description": (
            "Convert image format with quality settings.\n\n"
            "Example: magick input.png -quality 85 output.jpg\n"
            "WebP: magick input.png -quality 80 output.webp"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string", "description": "Output path (format inferred from extension)."},
                "quality": {"type": "integer", "description": "Quality 1-100 (for lossy formats).", "default": 90},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_optimize",
        "description": (
            "Optimize image file size by stripping metadata, reducing colors, etc.\n\n"
            "Example: magick input.png -strip -colors 256 -depth 8 output.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "strip_metadata": {"type": "boolean", "default": True},
                "max_colors": {"type": "integer", "description": "Max colors (0 = no limit).", "default": 0},
                "depth": {"type": "integer", "description": "Bit depth per channel.", "default": 8},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_thumbnail",
        "description": (
            "Generate thumbnails efficiently (faster than resize for large images).\n\n"
            "Example: magick input.png -thumbnail 320x180 thumb.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string"},
                "output": {"type": "string"},
                "width": {"type": "integer", "default": 320},
                "height": {"type": "integer", "default": 180},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "imagemagick_gif_create",
        "description": (
            "Create an animated GIF from a sequence of image frames.\n\n"
            "Example: magick -delay 10 -loop 0 frame_*.png animation.gif\n"
            "With optimization: magick -delay 10 -loop 0 frame_*.png "
            "-layers OptimizePlus -colors 128 animation.gif"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "frames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of frame image paths.",
                },
                "output": {"type": "string"},
                "delay": {"type": "integer", "description": "Delay between frames in centiseconds (10 = 100ms).", "default": 10},
                "loop": {"type": "integer", "description": "Loop count (0 = infinite).", "default": 0},
                "optimize": {"type": "boolean", "description": "Apply frame optimization.", "default": True},
                "max_colors": {"type": "integer", "default": 256},
            },
            "required": ["frames", "output"],
        },
    },
]

# ======================================================================
# FFMPEG TOOLS
# ======================================================================

FFMPEG_TOOLS: list[dict] = [
    # --- ANALYSIS ---
    {
        "name": "ffmpeg_probe",
        "description": (
            "Get detailed media file info: duration, resolution, codec, bitrate, "
            "frame rate, audio channels, sample rate.\n\n"
            "Example: ffprobe -v quiet -print_format json -show_format -show_streams input.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string", "description": "Media file to analyze."},
            },
            "required": ["input_file"],
        },
    },
    {
        "name": "ffmpeg_loudness",
        "description": (
            "Measure audio loudness in LUFS (EBU R128).\n\n"
            "Example: ffmpeg -i input.mp4 -af loudnorm=print_format=json -f null -"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
            },
            "required": ["input_file"],
        },
    },
    {
        "name": "ffmpeg_scene_detect",
        "description": (
            "Detect scene changes in a video. Returns timestamps of cuts.\n\n"
            "Example: ffmpeg -i input.mp4 -vf \"select='gt(scene,0.3)',showinfo\" -f null -"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "threshold": {
                    "type": "number",
                    "description": "Scene change threshold 0.0-1.0 (lower = more sensitive).",
                    "default": 0.3,
                },
            },
            "required": ["input_file"],
        },
    },
    # --- VIDEO FILTERS ---
    {
        "name": "ffmpeg_color_grade",
        "description": (
            "Apply color grading using LUTs, color curves, or level adjustments.\n\n"
            "LUT: ffmpeg -i input.mp4 -vf lut3d=file=grade.cube output.mp4\n"
            "Curves: ffmpeg -i input.mp4 -vf curves=preset=lighter output.mp4\n"
            "Eq: ffmpeg -i input.mp4 -vf eq=brightness=0.06:contrast=1.2:saturation=1.3 output.mp4\n"
            "Presets for curves: none, color_negative, cross_process, darker, "
            "increase_contrast, lighter, linear_contrast, medium_contrast, "
            "negative, strong_contrast, vintage"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "method": {
                    "type": "string",
                    "enum": ["lut3d", "curves", "eq", "colorbalance", "colorchannelmixer"],
                    "default": "eq",
                },
                "lut_file": {"type": "string", "description": "Path to .cube LUT file (for lut3d method)."},
                "curves_preset": {
                    "type": "string",
                    "description": "Preset for curves method.",
                    "enum": [
                        "none", "color_negative", "cross_process", "darker",
                        "increase_contrast", "lighter", "linear_contrast",
                        "medium_contrast", "negative", "strong_contrast", "vintage",
                    ],
                },
                "brightness": {"type": "number", "description": "Brightness for eq method (-1.0 to 1.0).", "default": 0},
                "contrast": {"type": "number", "description": "Contrast for eq method (0.0 to 2.0).", "default": 1.0},
                "saturation": {"type": "number", "description": "Saturation for eq method (0.0 to 3.0).", "default": 1.0},
                "gamma": {"type": "number", "description": "Gamma for eq method.", "default": 1.0},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_chromakey",
        "description": (
            "Remove green/blue screen background from video.\n\n"
            "Example: ffmpeg -i greenscreen.mp4 -vf \"chromakey=0x00FF00:0.3:0.1\" -c:a copy output.mp4\n"
            "With background: ffmpeg -i bg.mp4 -i greenscreen.mp4 "
            "-filter_complex \"[1:v]chromakey=0x00FF00:0.3:0.1[fg];[0:v][fg]overlay\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string", "description": "Green/blue screen video."},
                "output": {"type": "string"},
                "color": {"type": "string", "description": "Key color in hex (e.g. '0x00FF00' for green).", "default": "0x00FF00"},
                "similarity": {"type": "number", "description": "Color similarity threshold 0.0-1.0.", "default": 0.3},
                "blend": {"type": "number", "description": "Edge blending 0.0-1.0.", "default": 0.1},
                "background_file": {"type": "string", "description": "Optional background video/image to composite onto."},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_overlay",
        "description": (
            "Overlay a video/image on top of another (picture-in-picture, watermark).\n\n"
            "PiP: ffmpeg -i main.mp4 -i pip.mp4 -filter_complex "
            "\"[1:v]scale=320:-1[pip];[0:v][pip]overlay=W-w-10:H-h-10\" output.mp4\n"
            "Watermark: ffmpeg -i video.mp4 -i logo.png -filter_complex "
            "\"[1:v]scale=100:-1,format=rgba,colorchannelmixer=aa=0.5[wm];[0:v][wm]overlay=10:10\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "main_input": {"type": "string", "description": "Main/background video."},
                "overlay_input": {"type": "string", "description": "Overlay video or image."},
                "output": {"type": "string"},
                "x": {"type": "string", "description": "X position (number or expression like 'W-w-10').", "default": "0"},
                "y": {"type": "string", "description": "Y position (number or expression like 'H-h-10').", "default": "0"},
                "scale_width": {"type": "integer", "description": "Scale overlay to this width (-1 for proportional).", "default": -1},
                "opacity": {"type": "number", "description": "Overlay opacity 0.0-1.0.", "default": 1.0},
                "enable_time": {"type": "string", "description": "Time expression for when overlay is visible, e.g. 'between(t,5,10)'."},
            },
            "required": ["main_input", "overlay_input", "output"],
        },
    },
    {
        "name": "ffmpeg_drawtext",
        "description": (
            "Burn text directly into a video with formatting and animation.\n\n"
            "Static: ffmpeg -i input.mp4 -vf \"drawtext=text='Hello':fontsize=48:"
            "fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2\" output.mp4\n"
            "Timed: ffmpeg -i input.mp4 -vf \"drawtext=text='Breaking':fontsize=72:"
            "fontcolor=red:x=50:y=50:enable='between(t,2,5)'\" output.mp4\n"
            "Scrolling: ffmpeg -i input.mp4 -vf \"drawtext=text='News Ticker':"
            "fontsize=36:fontcolor=white:x=w-mod(t*100\\,w+text_w):y=h-50\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "text": {"type": "string", "description": "Text to display."},
                "fontfile": {"type": "string", "description": "Path to font file (.ttf/.otf)."},
                "fontsize": {"type": "integer", "default": 48},
                "fontcolor": {"type": "string", "default": "white"},
                "x": {"type": "string", "description": "X position (number or expression).", "default": "(w-text_w)/2"},
                "y": {"type": "string", "description": "Y position (number or expression).", "default": "(h-text_h)/2"},
                "box": {"type": "boolean", "description": "Draw background box behind text.", "default": False},
                "boxcolor": {"type": "string", "description": "Box background color.", "default": "black@0.5"},
                "boxborderw": {"type": "integer", "description": "Box padding in pixels.", "default": 10},
                "enable": {"type": "string", "description": "Time expression when text is visible, e.g. 'between(t,2,5)'."},
                "shadowcolor": {"type": "string", "description": "Text shadow color."},
                "shadowx": {"type": "integer", "description": "Shadow X offset.", "default": 2},
                "shadowy": {"type": "integer", "description": "Shadow Y offset.", "default": 2},
            },
            "required": ["input_file", "output", "text"],
        },
    },
    {
        "name": "ffmpeg_scale",
        "description": (
            "Resize video, optionally with padding to maintain aspect ratio.\n\n"
            "Scale: ffmpeg -i input.mp4 -vf scale=1920:1080 output.mp4\n"
            "Scale + pad: ffmpeg -i input.mp4 -vf \"scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
                "pad": {"type": "boolean", "description": "Pad to exact size (preserving aspect ratio).", "default": False},
                "pad_color": {"type": "string", "default": "black"},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_crop",
        "description": (
            "Crop a region from a video.\n\n"
            "Example: ffmpeg -i input.mp4 -vf \"crop=1280:720:320:180\" output.mp4\n"
            "Center crop: ffmpeg -i input.mp4 -vf \"crop=1280:720\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "x": {"type": "string", "description": "X offset (number or expression like '(in_w-1280)/2').", "default": "(in_w-ow)/2"},
                "y": {"type": "string", "description": "Y offset.", "default": "(in_h-oh)/2"},
            },
            "required": ["input_file", "output", "width", "height"],
        },
    },
    {
        "name": "ffmpeg_speed",
        "description": (
            "Speed up or slow down video and/or audio.\n\n"
            "2x speed: ffmpeg -i input.mp4 -vf setpts=0.5*PTS -af atempo=2.0 output.mp4\n"
            "0.5x slow: ffmpeg -i input.mp4 -vf setpts=2.0*PTS -af atempo=0.5 output.mp4\n"
            "Note: atempo only supports 0.5-2.0; for larger changes, chain multiple atempo filters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "speed": {"type": "number", "description": "Speed multiplier (2.0 = 2x fast, 0.5 = half speed).", "default": 2.0},
                "adjust_audio": {"type": "boolean", "description": "Also adjust audio speed.", "default": True},
            },
            "required": ["input_file", "output", "speed"],
        },
    },
    {
        "name": "ffmpeg_reverse",
        "description": (
            "Reverse video and/or audio.\n\n"
            "Example: ffmpeg -i input.mp4 -vf reverse -af areverse output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "reverse_audio": {"type": "boolean", "default": True},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_loop",
        "description": (
            "Loop a video or audio file a specified number of times.\n\n"
            "Example: ffmpeg -stream_loop 3 -i input.mp4 -c copy output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "count": {"type": "integer", "description": "Number of loops (-1 for infinite, 0 = play once).", "default": 3},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_trim",
        "description": (
            "Cut a video segment by start/end time.\n\n"
            "Example: ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45 -c copy output.mp4\n"
            "With re-encode: ffmpeg -ss 00:01:30 -i input.mp4 -to 00:01:15 -c:v libx264 -c:a aac output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "start": {"type": "string", "description": "Start time (HH:MM:SS or seconds).", "default": "00:00:00"},
                "end": {"type": "string", "description": "End time (HH:MM:SS or seconds)."},
                "duration": {"type": "string", "description": "Duration from start (alternative to end)."},
                "copy_codec": {"type": "boolean", "description": "Use -c copy for fast trim (may be imprecise).", "default": True},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_concat",
        "description": (
            "Concatenate multiple videos into one.\n\n"
            "Demuxer (fast, same codec): Create filelist.txt with lines 'file path.mp4', "
            "then: ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4\n"
            "Filter (different codecs): ffmpeg -i a.mp4 -i b.mp4 "
            "-filter_complex \"[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]\" "
            "-map \"[v]\" -map \"[a]\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of video file paths to concatenate (in order).",
                },
                "output": {"type": "string"},
                "method": {
                    "type": "string",
                    "enum": ["demuxer", "filter"],
                    "description": "demuxer = fast (same codec). filter = re-encode (different codecs/resolutions).",
                    "default": "demuxer",
                },
            },
            "required": ["inputs", "output"],
        },
    },
    {
        "name": "ffmpeg_crossfade",
        "description": (
            "Apply a crossfade transition between two clips.\n\n"
            "Example: ffmpeg -i clip1.mp4 -i clip2.mp4 "
            "-filter_complex \"[0:v][1:v]xfade=transition=fade:duration=1:offset=4[v];"
            "[0:a][1:a]acrossfade=d=1[a]\" -map \"[v]\" -map \"[a]\" output.mp4\n\n"
            "Available transitions: fade, wipeleft, wiperight, wipeup, wipedown, "
            "slideleft, slideright, slideup, slidedown, circlecrop, rectcrop, "
            "distance, fadeblack, fadewhite, radial, smoothleft, smoothright, "
            "smoothup, smoothdown, circleopen, circleclose, vertopen, vertclose, "
            "horzopen, horzclose, dissolve, pixelize, diagtl, diagtr, diagbl, diagbr, "
            "hlslice, hrslice, vuslice, vdslice, hblur, fadegrays, squeezeh, squeezev, "
            "zoomin, hlwind, hrwind, vuwind, vdwind, coverleft, coverright, "
            "coverup, coverdown, revealleft, revealright, revealup, revealdown"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_a": {"type": "string"},
                "clip_b": {"type": "string"},
                "output": {"type": "string"},
                "transition": {
                    "type": "string",
                    "description": "Transition type.",
                    "default": "fade",
                },
                "duration": {"type": "number", "description": "Crossfade duration in seconds.", "default": 1.0},
                "offset": {"type": "number", "description": "Offset in clip_a where transition starts (seconds). Should be clip_a_duration - crossfade_duration."},
            },
            "required": ["clip_a", "clip_b", "output"],
        },
    },
    {
        "name": "ffmpeg_fade",
        "description": (
            "Apply fade in/out to a video.\n\n"
            "Fade in: ffmpeg -i input.mp4 -vf \"fade=t=in:st=0:d=2\" -af \"afade=t=in:st=0:d=2\" output.mp4\n"
            "Fade out: ffmpeg -i input.mp4 -vf \"fade=t=out:st=8:d=2\" -af \"afade=t=out:st=8:d=2\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "type": {"type": "string", "enum": ["in", "out", "both"], "default": "both"},
                "duration": {"type": "number", "description": "Fade duration in seconds.", "default": 2.0},
                "start_time": {"type": "number", "description": "Start time for fade out (ignored for fade in).", "default": 0},
                "fade_audio": {"type": "boolean", "default": True},
                "color": {"type": "string", "description": "Fade to/from color.", "default": "black"},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_blur_region",
        "description": (
            "Blur a specific rectangular region in a video (face blur, license plate, etc.).\n\n"
            "Example: ffmpeg -i input.mp4 -vf "
            "\"split[main][blur];[blur]crop=200:200:100:50,boxblur=20[blurred];"
            "[main][blurred]overlay=100:50\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "x": {"type": "integer", "description": "Region X position."},
                "y": {"type": "integer", "description": "Region Y position."},
                "width": {"type": "integer", "description": "Region width."},
                "height": {"type": "integer", "description": "Region height."},
                "blur_strength": {"type": "integer", "description": "Box blur strength.", "default": 20},
                "enable": {"type": "string", "description": "Time expression for when blur is active."},
            },
            "required": ["input_file", "output", "x", "y", "width", "height"],
        },
    },
    {
        "name": "ffmpeg_stabilize",
        "description": (
            "Stabilize shaky video using the vidstab filter (two-pass).\n\n"
            "Pass 1 (analysis): ffmpeg -i input.mp4 -vf vidstabdetect=shakiness=5 -f null -\n"
            "Pass 2 (transform): ffmpeg -i input.mp4 -vf vidstabtransform=smoothing=10 output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "shakiness": {"type": "integer", "description": "Detection sensitivity 1-10.", "default": 5},
                "smoothing": {"type": "integer", "description": "Smoothing strength (frames).", "default": 10},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_denoise",
        "description": (
            "Apply video denoising.\n\n"
            "hqdn3d (fast): ffmpeg -i input.mp4 -vf hqdn3d=4:3:6:4.5 output.mp4\n"
            "nlmeans (slow, better): ffmpeg -i input.mp4 -vf nlmeans=s=3:p=7:r=5 output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "method": {"type": "string", "enum": ["hqdn3d", "nlmeans"], "default": "hqdn3d"},
                "strength": {"type": "number", "description": "Denoising strength (1-10).", "default": 4},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_eq",
        "description": (
            "Video equalizer: adjust brightness, contrast, saturation, gamma.\n\n"
            "Example: ffmpeg -i input.mp4 -vf eq=brightness=0.06:contrast=1.2:saturation=1.3:gamma=1.1 output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "brightness": {"type": "number", "description": "Brightness (-1.0 to 1.0, 0=unchanged).", "default": 0},
                "contrast": {"type": "number", "description": "Contrast (0.0 to 2.0, 1.0=unchanged).", "default": 1.0},
                "saturation": {"type": "number", "description": "Saturation (0.0 to 3.0, 1.0=unchanged).", "default": 1.0},
                "gamma": {"type": "number", "description": "Gamma (0.1 to 10.0, 1.0=unchanged).", "default": 1.0},
                "gamma_r": {"type": "number", "description": "Red channel gamma.", "default": 1.0},
                "gamma_g": {"type": "number", "description": "Green channel gamma.", "default": 1.0},
                "gamma_b": {"type": "number", "description": "Blue channel gamma.", "default": 1.0},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_extract_frames",
        "description": (
            "Extract frames from video as images.\n\n"
            "Every frame: ffmpeg -i input.mp4 frames/frame_%04d.png\n"
            "1 fps: ffmpeg -i input.mp4 -vf fps=1 frames/frame_%04d.png\n"
            "Specific time: ffmpeg -i input.mp4 -ss 00:01:30 -frames:v 1 frame.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output_pattern": {"type": "string", "description": "Output pattern, e.g. 'frames/frame_%04d.png'.", "default": "frames/frame_%04d.png"},
                "fps": {"type": "number", "description": "Frames per second to extract (0 = all frames).", "default": 1},
                "start_time": {"type": "string", "description": "Start time."},
                "duration": {"type": "string", "description": "Duration to extract."},
                "max_frames": {"type": "integer", "description": "Maximum number of frames (0 = no limit).", "default": 0},
            },
            "required": ["input_file"],
        },
    },
    {
        "name": "ffmpeg_create_video_from_images",
        "description": (
            "Create a video from an image sequence.\n\n"
            "Example: ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4\n"
            "With audio: ffmpeg -framerate 30 -i frame_%04d.png -i audio.mp3 "
            "-c:v libx264 -pix_fmt yuv420p -shortest output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_pattern": {"type": "string", "description": "Image sequence pattern, e.g. 'frame_%04d.png'."},
                "output": {"type": "string"},
                "framerate": {"type": "integer", "default": 30},
                "audio_file": {"type": "string", "description": "Optional audio track to add."},
                "codec": {"type": "string", "default": "libx264"},
                "pixel_format": {"type": "string", "default": "yuv420p"},
            },
            "required": ["input_pattern", "output"],
        },
    },
    {
        "name": "ffmpeg_gif",
        "description": (
            "Create a GIF from a video segment.\n\n"
            "High quality: ffmpeg -i input.mp4 -vf \"fps=15,scale=480:-1:flags=lanczos,"
            "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse\" output.gif"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "fps": {"type": "integer", "default": 15},
                "width": {"type": "integer", "description": "Output width (-1 for proportional).", "default": 480},
                "start": {"type": "string", "description": "Start time."},
                "duration": {"type": "string", "description": "Duration."},
                "high_quality": {"type": "boolean", "description": "Use palette generation for better quality.", "default": True},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_zoom_pan",
        "description": (
            "Ken Burns effect: slow zoom and pan on a still image to create video.\n\n"
            "Zoom in: ffmpeg -loop 1 -i image.png -vf "
            "\"scale=8000:-1,zoompan=z='min(zoom+0.001,1.5)':d=150:x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':s=1920x1080\" -t 5 -c:v libx264 -pix_fmt yuv420p output.mp4\n"
            "Pan: ffmpeg -loop 1 -i image.png -vf "
            "\"scale=3840:-1,zoompan=z=1:d=150:x='min(iw-iw/zoom,max(0,trunc(iw/2-(iw/zoom/2)+on*2)))':"
            "y='ih/2-(ih/zoom/2)':s=1920x1080\" -t 5 output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_image": {"type": "string", "description": "Still image to animate."},
                "output": {"type": "string"},
                "duration": {"type": "number", "description": "Output video duration in seconds.", "default": 5},
                "zoom_start": {"type": "number", "description": "Starting zoom level (1.0 = no zoom).", "default": 1.0},
                "zoom_end": {"type": "number", "description": "Ending zoom level.", "default": 1.5},
                "pan_direction": {
                    "type": "string",
                    "enum": ["none", "left", "right", "up", "down"],
                    "default": "none",
                },
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
                "fps": {"type": "integer", "default": 30},
            },
            "required": ["input_image", "output"],
        },
    },
    {
        "name": "ffmpeg_split_screen",
        "description": (
            "Create side-by-side or stacked video from two inputs.\n\n"
            "Side by side: ffmpeg -i left.mp4 -i right.mp4 "
            "-filter_complex \"[0:v]scale=960:1080[left];[1:v]scale=960:1080[right];"
            "[left][right]hstack=inputs=2\" output.mp4\n"
            "Stacked: ... vstack=inputs=2 ..."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "left_or_top": {"type": "string", "description": "Left (or top) video."},
                "right_or_bottom": {"type": "string", "description": "Right (or bottom) video."},
                "output": {"type": "string"},
                "layout": {"type": "string", "enum": ["horizontal", "vertical"], "default": "horizontal"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
            },
            "required": ["left_or_top", "right_or_bottom", "output"],
        },
    },
    # --- AUDIO FILTERS ---
    {
        "name": "ffmpeg_audio_normalize",
        "description": (
            "Normalize audio to EBU R128 loudness standard (recommended for YouTube: -14 LUFS).\n\n"
            "Two-pass: First measure, then apply.\n"
            "Example: ffmpeg -i input.mp4 -af loudnorm=I=-14:TP=-1:LRA=11 -c:v copy output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "target_lufs": {"type": "number", "description": "Target integrated loudness in LUFS.", "default": -14},
                "true_peak": {"type": "number", "description": "Maximum true peak in dBTP.", "default": -1},
                "lra": {"type": "number", "description": "Loudness range target.", "default": 11},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_audio_compress",
        "description": (
            "Apply dynamic range compression to audio.\n\n"
            "Example: ffmpeg -i input.mp4 -af \"acompressor=threshold=-20dB:ratio=4:attack=5:release=50\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "threshold_db": {"type": "number", "default": -20},
                "ratio": {"type": "number", "default": 4},
                "attack_ms": {"type": "number", "default": 5},
                "release_ms": {"type": "number", "default": 50},
                "makeup_db": {"type": "number", "description": "Makeup gain in dB.", "default": 0},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_audio_eq",
        "description": (
            "Apply parametric equalizer to audio.\n\n"
            "Example: ffmpeg -i input.mp4 -af \"equalizer=f=100:t=h:w=200:g=-5,"
            "equalizer=f=3000:t=h:w=2000:g=3\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "bands": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "frequency": {"type": "number", "description": "Center frequency in Hz."},
                            "width": {"type": "number", "description": "Bandwidth in Hz."},
                            "gain": {"type": "number", "description": "Gain in dB."},
                        },
                        "required": ["frequency", "gain"],
                    },
                    "description": "EQ bands to apply.",
                },
            },
            "required": ["input_file", "output", "bands"],
        },
    },
    {
        "name": "ffmpeg_audio_mix",
        "description": (
            "Mix multiple audio tracks together (e.g., voiceover + music).\n\n"
            "Example: ffmpeg -i voice.mp3 -i music.mp3 "
            "-filter_complex \"[0:a]volume=1.0[v];[1:a]volume=0.3[m];[v][m]amix=inputs=2:duration=first\" output.mp3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "volume": {"type": "number", "description": "Volume multiplier (1.0 = unchanged).", "default": 1.0},
                        },
                        "required": ["file"],
                    },
                },
                "output": {"type": "string"},
                "duration_mode": {
                    "type": "string",
                    "enum": ["longest", "shortest", "first"],
                    "description": "How to handle different-length inputs.",
                    "default": "first",
                },
            },
            "required": ["inputs", "output"],
        },
    },
    {
        "name": "ffmpeg_audio_duck",
        "description": (
            "Auto-duck background music when voiceover is present.\n\n"
            "Example: ffmpeg -i voice.mp3 -i music.mp3 "
            "-filter_complex \"[0:a]asplit=2[voice][sc];[sc]silencedetect=n=-30dB[det];"
            "[1:a][det]sidechaincompress=threshold=0.02:ratio=6:attack=200:release=1000[ducked];"
            "[voice][ducked]amix=inputs=2\" output.mp3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "voiceover": {"type": "string", "description": "Voiceover audio file."},
                "music": {"type": "string", "description": "Background music file."},
                "output": {"type": "string"},
                "duck_amount_db": {"type": "number", "description": "How much to reduce music (negative dB).", "default": -15},
                "attack_ms": {"type": "number", "description": "Duck attack time.", "default": 200},
                "release_ms": {"type": "number", "description": "Duck release time.", "default": 1000},
            },
            "required": ["voiceover", "music", "output"],
        },
    },
    {
        "name": "ffmpeg_audio_fade",
        "description": (
            "Apply audio fade in/out.\n\n"
            "Fade in: ffmpeg -i input.mp3 -af \"afade=t=in:st=0:d=3\" output.mp3\n"
            "Fade out: ffmpeg -i input.mp3 -af \"afade=t=out:st=57:d=3\" output.mp3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "type": {"type": "string", "enum": ["in", "out", "both"], "default": "both"},
                "duration": {"type": "number", "description": "Fade duration in seconds.", "default": 3.0},
                "start_time": {"type": "number", "description": "Start time for fade out."},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_audio_extract",
        "description": (
            "Extract audio from a video file.\n\n"
            "Copy: ffmpeg -i video.mp4 -vn -acodec copy audio.aac\n"
            "Convert: ffmpeg -i video.mp4 -vn -ar 44100 -ac 2 -b:a 192k audio.mp3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string", "description": "Output audio path (format inferred from extension)."},
                "codec": {"type": "string", "description": "Audio codec (copy, aac, libmp3lame, pcm_s16le, etc.).", "default": "copy"},
                "sample_rate": {"type": "integer", "description": "Sample rate (e.g. 44100, 48000).", "default": 44100},
                "bitrate": {"type": "string", "description": "Audio bitrate (e.g. '192k').", "default": "192k"},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_vignette",
        "description": (
            "Add a vignette (edge darkening) effect to video.\n\n"
            "Example: ffmpeg -i input.mp4 -vf \"vignette=PI/4\" output.mp4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "angle": {"type": "string", "description": "Vignette angle expression (e.g. 'PI/4').", "default": "PI/4"},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "ffmpeg_thumbnail_sheet",
        "description": (
            "Create a thumbnail contact sheet from a video.\n\n"
            "Example: ffmpeg -i input.mp4 -vf \"select='not(mod(n,30))',scale=320:180,tile=5x4\" "
            "-frames:v 1 thumbnails.png"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "columns": {"type": "integer", "default": 5},
                "rows": {"type": "integer", "default": 4},
                "thumb_width": {"type": "integer", "default": 320},
                "thumb_height": {"type": "integer", "default": 180},
            },
            "required": ["input_file", "output"],
        },
    },
]

# ======================================================================
# SOX TOOLS
# ======================================================================

SOX_TOOLS: list[dict] = [
    {
        "name": "sox_normalize",
        "description": (
            "Normalize audio to peak level or RMS level.\n\n"
            "Peak: sox input.wav output.wav norm -1\n"
            "RMS: sox input.wav output.wav norm -3 (normalize to -3 dB)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "level_db": {"type": "number", "description": "Target level in dB (negative, e.g. -1).", "default": -1},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_trim",
        "description": (
            "Trim audio by start time and duration.\n\n"
            "Example: sox input.wav output.wav trim 5.0 10.0  (start at 5s, duration 10s)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "start": {"type": "number", "description": "Start time in seconds.", "default": 0},
                "duration": {"type": "number", "description": "Duration in seconds (0 = to end).", "default": 0},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_fade",
        "description": (
            "Apply fade in and/or fade out to audio.\n\n"
            "Fade in: sox input.wav output.wav fade t 3 0 0\n"
            "Fade out (3s at end): sox input.wav output.wav fade t 0 0 3\n"
            "Both: sox input.wav output.wav fade t 2 0 3\n"
            "Types: t=triangle(linear), q=quarter-sine, h=half-sine, l=logarithmic, p=inverted-parabola"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "fade_in": {"type": "number", "description": "Fade in duration (seconds).", "default": 0},
                "fade_out": {"type": "number", "description": "Fade out duration (seconds).", "default": 0},
                "fade_type": {"type": "string", "enum": ["t", "q", "h", "l", "p"], "description": "Fade curve type.", "default": "t"},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_reverb",
        "description": (
            "Add reverb effect to audio.\n\n"
            "Example: sox input.wav output.wav reverb 50 50 100 100 0 0"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "reverberance": {"type": "number", "description": "Reverberance percent (0-100).", "default": 50},
                "hf_damping": {"type": "number", "description": "HF damping percent.", "default": 50},
                "room_scale": {"type": "number", "description": "Room scale percent.", "default": 100},
                "stereo_depth": {"type": "number", "description": "Stereo depth percent.", "default": 100},
                "wet_only": {"type": "boolean", "description": "Output only the wet (reverb) signal.", "default": False},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_echo",
        "description": (
            "Add echo effect.\n\n"
            "Example: sox input.wav output.wav echo 0.8 0.88 60 0.4\n"
            "Multiple: sox input.wav output.wav echo 0.8 0.88 60 0.4 100 0.3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "gain_in": {"type": "number", "default": 0.8},
                "gain_out": {"type": "number", "default": 0.88},
                "delays": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "delay_ms": {"type": "number"},
                            "decay": {"type": "number"},
                        },
                        "required": ["delay_ms", "decay"],
                    },
                    "description": "List of echo delay/decay pairs.",
                },
            },
            "required": ["input_file", "output", "delays"],
        },
    },
    {
        "name": "sox_compand",
        "description": (
            "Dynamic range compression/expansion using SoX compand.\n\n"
            "Compression: sox input.wav output.wav compand 0.3,1 6:-70,-60,-20 -5 -90 0.2\n"
            "Voice: sox input.wav output.wav compand 0.02,0.2 -60,-60,-30,-15,-20,-12,-4,-4,0,-3"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "attack_decay": {"type": "string", "description": "Attack,decay in seconds (e.g. '0.3,1').", "default": "0.3,1"},
                "transfer_function": {"type": "string", "description": "Transfer function dB pairs (e.g. '6:-70,-60,-20').", "default": "6:-70,-60,-20"},
                "gain_db": {"type": "number", "description": "Output gain in dB.", "default": -5},
                "initial_level_db": {"type": "number", "description": "Initial volume level.", "default": -90},
                "delay": {"type": "number", "description": "Lookahead delay in seconds.", "default": 0.2},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_equalizer",
        "description": (
            "Apply parametric EQ band.\n\n"
            "Example: sox input.wav output.wav equalizer 1000 1q 5\n"
            "Multiple: sox input.wav output.wav equalizer 200 2q -3 equalizer 5000 1q 4"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "bands": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "frequency": {"type": "number", "description": "Center frequency in Hz."},
                            "q": {"type": "number", "description": "Q factor (bandwidth).", "default": 1.0},
                            "gain_db": {"type": "number", "description": "Gain in dB."},
                        },
                        "required": ["frequency", "gain_db"],
                    },
                },
            },
            "required": ["input_file", "output", "bands"],
        },
    },
    {
        "name": "sox_bass",
        "description": (
            "Boost or cut bass frequencies.\n\n"
            "Boost: sox input.wav output.wav bass +6 100\n"
            "Cut: sox input.wav output.wav bass -3 200"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "gain_db": {"type": "number", "description": "Gain in dB (positive=boost, negative=cut).", "default": 6},
                "frequency": {"type": "number", "description": "Center frequency in Hz.", "default": 100},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_treble",
        "description": (
            "Boost or cut treble frequencies.\n\n"
            "Boost: sox input.wav output.wav treble +4 3000\n"
            "Cut: sox input.wav output.wav treble -3 5000"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "gain_db": {"type": "number", "default": 4},
                "frequency": {"type": "number", "default": 3000},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_speed",
        "description": (
            "Change playback speed without changing pitch (time-stretch).\n\n"
            "Example: sox input.wav output.wav tempo 1.5  (1.5x speed, pitch preserved)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "factor": {"type": "number", "description": "Speed factor (1.5 = 50% faster).", "default": 1.5},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_pitch",
        "description": (
            "Change pitch without changing speed.\n\n"
            "Example: sox input.wav output.wav pitch 200  (shift up 200 cents / 2 semitones)\n"
            "Down: sox input.wav output.wav pitch -300  (shift down 3 semitones)"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "cents": {"type": "integer", "description": "Pitch shift in cents (100 cents = 1 semitone).", "default": 200},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_noise_profile",
        "description": (
            "Create a noise profile from a sample of background noise. "
            "This is step 1 of noise reduction -- record or trim a short segment "
            "of just the noise, then create a profile.\n\n"
            "Example: sox noisy.wav -n trim 0 0.5 noiseprof noise.prof"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string", "description": "Audio file with a noise-only segment."},
                "output_profile": {"type": "string", "description": "Output noise profile file path."},
                "start": {"type": "number", "description": "Start of noise segment (seconds).", "default": 0},
                "duration": {"type": "number", "description": "Duration of noise segment.", "default": 0.5},
            },
            "required": ["input_file", "output_profile"],
        },
    },
    {
        "name": "sox_noise_reduce",
        "description": (
            "Reduce noise using a noise profile (created by sox_noise_profile).\n\n"
            "Example: sox noisy.wav clean.wav noisered noise.prof 0.21"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "noise_profile": {"type": "string", "description": "Path to noise profile file."},
                "amount": {"type": "number", "description": "Noise reduction amount 0.0-1.0 (higher=more aggressive).", "default": 0.21},
            },
            "required": ["input_file", "output", "noise_profile"],
        },
    },
    {
        "name": "sox_silence_remove",
        "description": (
            "Remove silence segments from audio.\n\n"
            "Example: sox input.wav output.wav silence 1 0.1 1% -1 0.1 1%\n"
            "This removes leading silence (1 period, 0.1s min, 1% threshold) "
            "and trailing silence (-1 period)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "threshold": {"type": "string", "description": "Silence threshold (e.g. '1%' or '-50d').", "default": "1%"},
                "min_duration": {"type": "number", "description": "Minimum silence duration to remove (seconds).", "default": 0.1},
            },
            "required": ["input_file", "output"],
        },
    },
    {
        "name": "sox_mix",
        "description": (
            "Mix (sum) multiple audio files together.\n\n"
            "Example: sox -m track1.wav track2.wav mix.wav\n"
            "With volume: sox -m -v 1.0 track1.wav -v 0.3 track2.wav mix.wav"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "volume": {"type": "number", "default": 1.0},
                        },
                        "required": ["file"],
                    },
                },
                "output": {"type": "string"},
            },
            "required": ["inputs", "output"],
        },
    },
    {
        "name": "sox_stats",
        "description": (
            "Get detailed audio statistics: RMS level, peak, duration, DC offset, etc.\n\n"
            "Example: sox input.wav -n stat"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
            },
            "required": ["input_file"],
        },
    },
    {
        "name": "sox_spectrogram",
        "description": (
            "Generate a spectrogram visualization image from audio.\n\n"
            "Example: sox input.wav -n spectrogram -o spectrogram.png -t 'Audio Spectrogram'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"},
                "output": {"type": "string"},
                "title": {"type": "string", "description": "Title for the spectrogram image.", "default": "Spectrogram"},
                "width": {"type": "integer", "description": "Image width in pixels.", "default": 800},
                "height": {"type": "integer", "description": "Image height in pixels.", "default": 400},
            },
            "required": ["input_file", "output"],
        },
    },
]

# ======================================================================
# PYTHON / PILLOW TOOLS
# ======================================================================

PYTHON_TOOLS: list[dict] = [
    {
        "name": "run_python_code",
        "description": (
            "Execute Python code for programmatic image manipulation using Pillow, "
            "NumPy, or other installed libraries. The work directory is available "
            "as the variable WORK_DIR. Imports of subprocess, socket, http, urllib "
            "are blocked for safety.\n\n"
            "Example:\n"
            "  from PIL import Image, ImageDraw, ImageFont\n"
            "  import os\n"
            "  img = Image.new('RGBA', (1920, 1080), (26, 26, 46, 255))\n"
            "  draw = ImageDraw.Draw(img)\n"
            "  draw.text((960, 540), 'Hello', fill='white', anchor='mm')\n"
            "  img.save(os.path.join(WORK_DIR, 'output.png'))"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. WORK_DIR variable is pre-set.",
                },
                "description": {
                    "type": "string",
                    "description": "What this code does.",
                },
            },
            "required": ["code"],
        },
    },
]

# ======================================================================
# FILE OPERATIONS
# ======================================================================

FILE_TOOLS: list[dict] = [
    {
        "name": "list_files",
        "description": (
            "List files in the work directory or a subdirectory. "
            "Returns file names, sizes, and types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Subdirectory to list (relative to work dir). Empty for root.",
                    "default": "",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter, e.g. '*.png'.",
                    "default": "*",
                },
            },
            "required": [],
        },
    },
    {
        "name": "copy_file",
        "description": "Copy a file within the work directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path (relative to work dir)."},
                "destination": {"type": "string", "description": "Destination path."},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "file_info",
        "description": "Get file size, type, and basic metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
]


# ======================================================================
# AGGREGATE FUNCTIONS
# ======================================================================

def get_all_power_tools() -> list[dict]:
    """Return all power tool definitions for Claude.

    These are formatted as Anthropic tool-use schemas ready to be passed
    to the ``tools`` parameter of ``client.messages.create()``.
    """
    all_tools = (
        SHELL_TOOLS
        + IMAGEMAGICK_TOOLS
        + FFMPEG_TOOLS
        + SOX_TOOLS
        + PYTHON_TOOLS
        + FILE_TOOLS
    )
    return all_tools


def get_tools_by_category(category: str) -> list[dict]:
    """Get tools for a specific category.

    Args:
        category: One of 'shell', 'imagemagick', 'ffmpeg', 'sox', 'python', 'file', 'all'.

    Returns:
        List of tool definition dicts.
    """
    mapping = {
        "shell": SHELL_TOOLS,
        "imagemagick": IMAGEMAGICK_TOOLS,
        "ffmpeg": FFMPEG_TOOLS,
        "sox": SOX_TOOLS,
        "python": PYTHON_TOOLS,
        "file": FILE_TOOLS,
        "all": get_all_power_tools(),
    }
    return mapping.get(category.lower(), [])


def get_tool_names() -> list[str]:
    """Return just the tool names for quick reference."""
    return [t["name"] for t in get_all_power_tools()]


def get_tool_by_name(name: str) -> dict | None:
    """Look up a specific tool definition by name."""
    for tool in get_all_power_tools():
        if tool["name"] == name:
            return tool
    return None
