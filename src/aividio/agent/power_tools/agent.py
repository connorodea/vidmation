"""Power Tools Agent -- CLI media manipulation sub-agent.

This agent is delegated to by the main orchestrator for tasks requiring
direct CLI tool access.  It can execute ImageMagick, FFmpeg, SoX, and
other command-line utilities to transform media files.

It operates in a sandboxed work directory and returns paths to output files.

Usage::

    from aividio.agent.power_tools import PowerToolsAgent

    agent = PowerToolsAgent(work_dir=Path("/tmp/pt_work"))
    result = agent.execute_task(
        task="Create a 1280x720 thumbnail with the title 'Top 10 Side Hustles' on a gradient background",
    )
    print(result["output_files"])
    print(result["commands_executed"])
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import anthropic

from aividio.agent.power_tools.capabilities import get_all_power_tools
from aividio.agent.power_tools.executors import CommandExecutor
from aividio.agent.power_tools.precheck import get_installed_tools
from aividio.config.settings import get_settings

logger = logging.getLogger(__name__)

# Maximum number of tool-use turns before we force the agent to stop.
_MAX_TURNS = 30

# Claude model to use for the sub-agent.
_MODEL = "claude-sonnet-4-20250514"

POWER_TOOLS_SYSTEM_PROMPT = """\
You are VIDMATION's Power Tools Agent -- a specialized media manipulation expert
with direct access to command-line tools.

You can execute any of the following CLI tools to transform images, video, and audio:

## IMAGE TOOLS
- **ImageMagick (magick)**: Image compositing, text rendering, effects, format conversion,
  color manipulation, filters, masks, gradients, annotations, montages
- **Pillow (via python)**: Programmatic image manipulation when ImageMagick syntax is awkward

## VIDEO TOOLS
- **FFmpeg**: Video encoding, filtering, compositing, overlays, color grading, speed changes,
  concatenation, format conversion, frame extraction, GIF creation
- **FFprobe**: Media file analysis and metadata extraction

## AUDIO TOOLS
- **SoX**: Audio processing, effects, format conversion, mixing, normalization,
  noise reduction, equalization, reverb, compression
- **FFmpeg audio filters**: Audio ducking, crossfades, volume adjustment, loudness normalization

## TEXT & GRAPHICS
- **ImageMagick text rendering**: Custom fonts, text effects, shadows, outlines, gradients on text,
  curved text, annotated images
- **Pango (via ImageMagick)**: Rich text layout with markup

## RULES
1. Always work within the provided work directory.  All file paths you use must be
   relative to the work directory.
2. Always validate inputs exist before processing.  Use list_files or file_info first.
3. Always check command results -- if a command fails, read the stderr and try to fix it.
4. Prefer single-pass operations over multi-step when possible.
5. When generating video, always use -pix_fmt yuv420p for broad compatibility.
6. For ImageMagick, prefer the `magick` command over `convert` (ImageMagick 7 syntax).
7. Always use -y flag with FFmpeg to overwrite without prompting.
8. When done, report what output files were created and what was done.

## AVAILABLE INPUT FILES
{input_files_description}

## INSTALLED TOOLS
{installed_tools_description}
"""


class PowerToolsAgent:
    """Sub-agent for CLI-based media manipulation.

    The orchestrator creates an instance of this agent, gives it a task
    in natural language plus any input files, and gets back output file
    paths and a description of what was done.
    """

    def __init__(
        self,
        settings: Any | None = None,
        work_dir: Path | None = None,
        timeout: int = 300,
    ):
        self.settings = settings or get_settings()
        self.client = anthropic.Anthropic(
            api_key=self.settings.anthropic_api_key.get_secret_value(),
        )
        self.work_dir = (work_dir or Path("data/work/power_tools")).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.executor = CommandExecutor(work_dir=self.work_dir, timeout=timeout)
        self.tools = self._build_tools()
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_task(
        self,
        task: str,
        input_files: dict[str, Path] | None = None,
    ) -> dict:
        """Execute a media manipulation task using CLI tools.

        Args:
            task: Natural language description of what to do.
            input_files: Dict mapping friendly names to file paths.
                         Files are validated and symlinked/copied into the work dir.

        Returns:
            A dict with keys:
            - ``output_files``: ``dict[str, Path]`` of name -> output path
            - ``description``: Human-readable description of what was done
            - ``commands_executed``: List of command dicts from the executor
            - ``success``: bool
            - ``error``: Optional error message if something went wrong
        """
        logger.info("PowerToolsAgent starting task: %s", task[:100])

        # Prepare input files in the work directory.
        prepared_inputs = self._prepare_inputs(input_files or {})

        try:
            result = self._run_agent_loop(task, prepared_inputs)
        except Exception as exc:
            logger.exception("PowerToolsAgent failed")
            result = {
                "output_files": {},
                "description": f"Agent failed with error: {exc}",
                "commands_executed": self.executor.get_history(),
                "success": False,
                "error": str(exc),
            }

        return result

    # ------------------------------------------------------------------
    # Agent loop
    # ------------------------------------------------------------------

    def _run_agent_loop(
        self,
        task: str,
        input_files: dict[str, Path],
    ) -> dict:
        """Run the sub-agent loop: Claude thinks -> calls tools -> we execute -> repeat."""

        # Build the system prompt with context about available tools and input files.
        system = self._build_system_prompt(input_files)

        messages: list[dict] = [
            {"role": "user", "content": task},
        ]

        output_files: dict[str, Path] = {}
        final_description = ""

        for turn in range(_MAX_TURNS):
            logger.debug("Agent loop turn %d/%d", turn + 1, _MAX_TURNS)

            response = self.client.messages.create(
                model=_MODEL,
                max_tokens=4096,
                system=system,
                tools=self.tools,
                messages=messages,
            )

            # Process the response.
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Check if the model wants to use tools.
            tool_use_blocks = [
                block for block in assistant_content if block.type == "tool_use"
            ]

            if not tool_use_blocks:
                # No tool calls -- the agent is done.  Extract final text.
                text_blocks = [
                    block.text for block in assistant_content if block.type == "text"
                ]
                final_description = "\n".join(text_blocks)
                break

            # Execute each tool call.
            tool_results: list[dict] = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tool_id = tool_block.id

                logger.debug("Executing tool: %s(%s)", tool_name, json.dumps(tool_input)[:200])

                try:
                    result = self._execute_tool(tool_name, tool_input, output_files)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                    })
                except Exception as exc:
                    logger.warning("Tool %s failed: %s", tool_name, exc)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps({"error": str(exc)}),
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})

            # Check stop reason.
            if response.stop_reason == "end_turn":
                break
        else:
            logger.warning("Agent loop reached max turns (%d)", _MAX_TURNS)
            final_description += "\n[WARNING: Agent reached maximum turn limit]"

        # Discover output files in the work directory.
        output_files = self._discover_outputs(output_files)

        self.history.append({
            "task": task,
            "input_files": {k: str(v) for k, v in input_files.items()},
            "output_files": {k: str(v) for k, v in output_files.items()},
            "description": final_description,
            "turns": min(turn + 1, _MAX_TURNS),
        })

        return {
            "output_files": output_files,
            "description": final_description,
            "commands_executed": self.executor.get_history(),
            "success": True,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(
        self,
        name: str,
        params: dict,
        output_files: dict[str, Path],
    ) -> dict:
        """Dispatch a tool call to the appropriate executor method."""

        # --- Shell command ---
        if name == "run_shell_command":
            return self.executor.run(
                command=params["command"],
                description=params.get("description", ""),
            )

        # --- ImageMagick tools ---
        if name.startswith("imagemagick_"):
            return self._execute_imagemagick(name, params)

        # --- FFmpeg tools ---
        if name.startswith("ffmpeg_"):
            return self._execute_ffmpeg(name, params)

        # --- SoX tools ---
        if name.startswith("sox_"):
            return self._execute_sox(name, params)

        # --- Python code ---
        if name == "run_python_code":
            return self.executor.run_python(
                code=params["code"],
            )

        # --- File operations ---
        if name == "list_files":
            return self._list_files(params)
        if name == "copy_file":
            return self._copy_file(params)
        if name == "file_info":
            return self._file_info(params)

        return {"error": f"Unknown tool: {name}"}

    def _execute_imagemagick(self, name: str, params: dict) -> dict:
        """Build and execute an ImageMagick command from structured parameters."""
        output = params.get("output", "output.png")

        # For tools that take an input image, we build the command args.
        if name == "imagemagick_composite":
            base = params["base_image"]
            overlay = params["overlay_image"]
            gravity = params.get("gravity", "NorthWest")
            compose = params.get("compose", "over")
            geometry = params.get("geometry", "+0+0")
            opacity = params.get("opacity", 100)

            if opacity < 100:
                alpha_val = opacity / 100.0
                args = [
                    base,
                    f"\\( {overlay} -alpha set -channel A -evaluate multiply {alpha_val:.2f} +channel \\)",
                    f"-gravity {gravity} -geometry {geometry}",
                    f"-compose {compose} -composite",
                ]
            else:
                args = [
                    base,
                    overlay,
                    f"-gravity {gravity} -geometry {geometry}",
                    f"-compose {compose} -composite",
                ]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_text":
            input_img = params["input_image"]
            text = params["text"].replace("'", "'\\''")
            font = params.get("font", "Arial-Bold")
            pointsize = params.get("pointsize", 48)
            fill = params.get("fill_color", "white")
            gravity = params.get("gravity", "Center")
            geometry = params.get("geometry", "+0+0")
            stroke = params.get("stroke_color", "")
            stroke_w = params.get("stroke_width", 0)
            shadow = params.get("shadow", False)

            cmd_parts = [input_img]

            if shadow:
                shadow_color = params.get("shadow_color", "black")
                shadow_offset = params.get("shadow_offset", "+2+2")
                shadow_blur = params.get("shadow_blur", 3)
                cmd_parts.append(
                    f"\\( +clone -gravity {gravity} -font {font} -pointsize {pointsize} "
                    f"-fill {shadow_color} -annotate {shadow_offset} '{text}' "
                    f"-blur 0x{shadow_blur} \\)"
                )

            cmd_parts.append(f"-gravity {gravity} -font {font} -pointsize {pointsize}")
            cmd_parts.append(f"-fill {fill}")

            if stroke and stroke_w > 0:
                cmd_parts.append(f"-stroke {stroke} -strokewidth {stroke_w}")

            cmd_parts.append(f"-annotate {geometry} '{text}'")
            return self.executor.run_imagemagick(cmd_parts, output)

        elif name == "imagemagick_annotate":
            input_img = params["input_image"]
            text = params["text"].replace("'", "'\\''")
            font = params.get("font", "Helvetica")
            pointsize = params.get("pointsize", 24)
            fill = params.get("fill_color", "white")
            gravity = params.get("gravity", "NorthWest")
            rotation = params.get("rotation", 0)
            geometry = params.get("geometry", "+0+0")

            annotate_spec = f"{rotation}x{rotation}{geometry}" if rotation else geometry
            args = [
                input_img,
                f"-gravity {gravity} -font {font} -pointsize {pointsize}",
                f"-fill '{fill}'",
                f"-annotate {annotate_spec} '{text}'",
            ]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_caption":
            text = params["text"].replace("'", "'\\''")
            w = params.get("width", 800)
            h = params.get("height", 200)
            font = params.get("font", "Arial")
            pointsize = params.get("pointsize", 0)
            fill = params.get("fill_color", "white")
            bg = params.get("background", "none")
            gravity = params.get("gravity", "Center")

            size_arg = f"-size {w}x{h}"
            pt_arg = f"-pointsize {pointsize}" if pointsize > 0 else ""
            args = [
                size_arg, f"-background {bg} -fill {fill}",
                f"-font {font} {pt_arg} -gravity {gravity}",
                f"caption:'{text}'",
            ]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_label":
            text = params["text"].replace("'", "'\\''")
            font = params.get("font", "Impact")
            pointsize = params.get("pointsize", 72)
            fill = params.get("fill_color", "white")
            bg = params.get("background", "none")

            args = [
                f"-background {bg} -fill {fill} -font {font}",
                f"-pointsize {pointsize} label:'{text}'",
            ]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_blur":
            input_img = params["input_image"]
            blur_type = params.get("type", "gaussian")
            radius = params.get("radius", 0)
            sigma = params.get("sigma", 8)
            angle = params.get("angle", 0)

            if blur_type == "motion":
                args = [input_img, f"-motion-blur {radius}x{sigma}+{angle}"]
            elif blur_type == "radial":
                args = [input_img, f"-radial-blur {sigma}"]
            else:
                args = [input_img, f"-blur {radius}x{sigma}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_sharpen":
            input_img = params["input_image"]
            sharpen_type = params.get("type", "unsharp")
            radius = params.get("radius", 0)
            sigma = params.get("sigma", 5)

            if sharpen_type == "unsharp":
                amount = params.get("amount", 1.5)
                threshold = params.get("threshold", 0.02)
                args = [input_img, f"-unsharp {radius}x{sigma}+{amount}+{threshold}"]
            else:
                args = [input_img, f"-sharpen {radius}x{sigma}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_shadow":
            input_img = params["input_image"]
            color = params.get("color", "black")
            opacity = params.get("opacity", 60)
            sigma = params.get("sigma", 5)
            x_off = params.get("x_offset", 5)
            y_off = params.get("y_offset", 5)

            args = [
                input_img,
                f"\\( +clone -background '{color}' -shadow {opacity}x{sigma}+{x_off}+{y_off} \\)",
                "+swap -background none -layers merge +repage",
            ]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_border":
            input_img = params["input_image"]
            border_type = params.get("type", "solid")
            width = params.get("width", 10)
            color = params.get("color", "white")

            if border_type == "solid":
                args = [input_img, f"-bordercolor '{color}' -border {width}"]
            elif border_type == "rounded":
                radius = params.get("corner_radius", 20)
                # Use a rounded rectangle mask approach.
                args = [
                    input_img,
                    f"\\( +clone -alpha extract -draw "
                    f"'fill black polygon 0,0 0,{radius} {radius},0 fill white circle {radius},{radius} {radius},0' "
                    f"\\( +clone -flip \\) -compose Multiply -composite "
                    f"\\( +clone -flop \\) -compose Multiply -composite \\) "
                    f"-alpha off -compose CopyOpacity -composite",
                ]
            else:  # frame
                args = [input_img, f"-mattecolor '{color}' -frame {width}x{width}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_gradient":
            w = params.get("width", 1920)
            h = params.get("height", 1080)
            grad_type = params.get("type", "linear")
            c_start = params.get("color_start", "#1a1a2e")
            c_end = params.get("color_end", "#16213e")

            if grad_type == "radial":
                args = [f"-size {w}x{h}", f"radial-gradient:'{c_start}'-'{c_end}'"]
            else:
                args = [f"-size {w}x{h}", f"gradient:'{c_start}'-'{c_end}'"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_vignette":
            input_img = params["input_image"]
            radius = params.get("radius", 0)
            sigma = params.get("sigma", 40)
            args = [input_img, f"-vignette {radius}x{sigma}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_colorize":
            input_img = params["input_image"]
            colorize_type = params.get("type", "tint")

            if colorize_type == "sepia":
                threshold = params.get("sepia_threshold", 80)
                args = [input_img, f"-sepia-tone {threshold}%"]
            elif colorize_type == "grayscale":
                args = [input_img, "-grayscale Rec709Luminance"]
            elif colorize_type == "duotone":
                shadow = params.get("duotone_shadow", "#1a1a2e")
                highlight = params.get("duotone_highlight", "#e94560")
                args = [
                    input_img, "-grayscale Rec709Luminance",
                    f"-fill '{shadow}' -colorize 100",
                    f"\\( {input_img} -grayscale Rec709Luminance -fill '{highlight}' -colorize 100 \\)",
                    "-compose screen -composite",
                ]
            else:  # tint
                color = params.get("color", "#e94560")
                amount = params.get("amount", 30)
                args = [input_img, f"-fill '{color}' -colorize {amount}%"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_brightness_contrast":
            input_img = params["input_image"]
            brightness = params.get("brightness", 0)
            contrast = params.get("contrast", 0)
            gamma = params.get("gamma", 1.0)

            args = [input_img]
            if brightness != 0 or contrast != 0:
                args.append(f"-brightness-contrast {brightness}x{contrast}")
            if gamma != 1.0:
                args.append(f"-gamma {gamma}")
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_hue_saturation":
            input_img = params["input_image"]
            hue = params.get("hue", 100)
            sat = params.get("saturation", 100)
            light = params.get("lightness", 100)
            args = [input_img, f"-modulate {light},{sat},{hue}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_resize":
            input_img = params["input_image"]
            w = params["width"]
            h = params["height"]
            mode = params.get("mode", "fit")
            filt = params.get("filter", "Lanczos")

            if mode == "fill":
                args = [input_img, f"-filter {filt}", f"-resize {w}x{h}^",
                        f"-gravity center -extent {w}x{h}"]
            elif mode == "exact":
                args = [input_img, f"-filter {filt}", f"-resize {w}x{h}!"]
            elif mode == "shrink_only":
                args = [input_img, f"-filter {filt}", f"-resize {w}x{h}>"]
            else:
                args = [input_img, f"-filter {filt}", f"-resize {w}x{h}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_crop":
            input_img = params["input_image"]
            w = params["width"]
            h = params["height"]
            x = params.get("x_offset", 0)
            y = params.get("y_offset", 0)
            gravity = params.get("gravity", "NorthWest")
            args = [input_img, f"-gravity {gravity}", f"-crop {w}x{h}+{x}+{y}", "+repage"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_rotate":
            input_img = params["input_image"]
            angle = params["angle"]
            bg = params.get("background", "none")
            args = [input_img, f"-background {bg} -rotate {angle}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_flip":
            input_img = params["input_image"]
            direction = params.get("direction", "horizontal")
            flag = "-flop" if direction == "horizontal" else "-flip"
            args = [input_img, flag]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_distort":
            input_img = params["input_image"]
            dist_type = params["type"]
            parameters = params["parameters"]
            bg = params.get("background", "none")
            type_map = {
                "perspective": "Perspective",
                "barrel": "Barrel",
                "arc": "Arc",
                "polar": "Polar",
                "depolar": "DePolar",
            }
            im_type = type_map.get(dist_type, dist_type.title())
            args = [input_img, f"-background {bg} -distort {im_type} '{parameters}'"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_montage":
            images = params["images"]
            tile = params.get("tile", "2x2")
            geometry = params.get("geometry", "640x360+5+5")
            bg = params.get("background", "#1a1a2e")
            # montage is a separate command.
            img_args = " ".join(images)
            cmd = (
                f"magick montage {img_args} -tile {tile} -geometry {geometry} "
                f"-background '{bg}' {output}"
            )
            return self.executor.run(cmd, description=f"Montage {len(images)} images")

        elif name == "imagemagick_append":
            images = params["images"]
            direction = params.get("direction", "horizontal")
            flag = "+append" if direction == "horizontal" else "-append"
            img_args = " ".join(images)
            args = [img_args, flag]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_mask":
            input_img = params["input_image"]
            mask = params["mask_image"]
            args = [input_img, mask, "-alpha Off -compose CopyOpacity -composite"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_convert":
            input_img = params["input_image"]
            quality = params.get("quality", 90)
            args = [input_img, f"-quality {quality}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_optimize":
            input_img = params["input_image"]
            args = [input_img]
            if params.get("strip_metadata", True):
                args.append("-strip")
            max_colors = params.get("max_colors", 0)
            if max_colors > 0:
                args.append(f"-colors {max_colors}")
            depth = params.get("depth", 8)
            args.append(f"-depth {depth}")
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_thumbnail":
            input_img = params["input_image"]
            w = params.get("width", 320)
            h = params.get("height", 180)
            args = [input_img, f"-thumbnail {w}x{h}"]
            return self.executor.run_imagemagick(args, output)

        elif name == "imagemagick_gif_create":
            frames = params["frames"]
            delay = params.get("delay", 10)
            loop = params.get("loop", 0)
            optimize = params.get("optimize", True)
            max_colors = params.get("max_colors", 256)

            frames_str = " ".join(frames)
            opt_args = f"-layers OptimizePlus -colors {max_colors}" if optimize else ""
            cmd = f"magick -delay {delay} -loop {loop} {frames_str} {opt_args} {output}"
            return self.executor.run(cmd, description=f"Create GIF from {len(frames)} frames")

        return {"error": f"Unhandled ImageMagick tool: {name}"}

    def _execute_ffmpeg(self, name: str, params: dict) -> dict:
        """Build and execute an FFmpeg/FFprobe command."""
        output = params.get("output", "output.mp4")

        if name == "ffmpeg_probe":
            input_file = params["input_file"]
            return self.executor.run(
                f"ffprobe -v quiet -print_format json -show_format -show_streams {input_file}",
                description="FFprobe analysis",
            )

        elif name == "ffmpeg_loudness":
            input_file = params["input_file"]
            return self.executor.run(
                f"ffmpeg -i {input_file} -af loudnorm=print_format=json -f null -",
                description="Measure loudness (LUFS)",
            )

        elif name == "ffmpeg_scene_detect":
            input_file = params["input_file"]
            threshold = params.get("threshold", 0.3)
            return self.executor.run(
                f"ffmpeg -i {input_file} -vf \"select='gt(scene,{threshold})',showinfo\" -f null -",
                description="Detect scene changes",
            )

        elif name == "ffmpeg_color_grade":
            input_file = params["input_file"]
            method = params.get("method", "eq")

            if method == "lut3d":
                lut_file = params.get("lut_file", "")
                args = [f"-i {input_file}", f"-vf lut3d=file={lut_file}", "-c:a copy"]
            elif method == "curves":
                preset = params.get("curves_preset", "lighter")
                args = [f"-i {input_file}", f"-vf curves=preset={preset}", "-c:a copy"]
            elif method == "colorbalance":
                args = [f"-i {input_file}", "-vf colorbalance=rs=0:gs=0:bs=0", "-c:a copy"]
            else:  # eq
                b = params.get("brightness", 0)
                c = params.get("contrast", 1.0)
                s = params.get("saturation", 1.0)
                g = params.get("gamma", 1.0)
                args = [
                    f"-i {input_file}",
                    f"-vf eq=brightness={b}:contrast={c}:saturation={s}:gamma={g}",
                    "-c:a copy",
                ]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_chromakey":
            input_file = params["input_file"]
            color = params.get("color", "0x00FF00")
            similarity = params.get("similarity", 0.3)
            blend = params.get("blend", 0.1)
            bg = params.get("background_file")

            if bg:
                args = [
                    f"-i {bg} -i {input_file}",
                    f"-filter_complex \"[1:v]chromakey={color}:{similarity}:{blend}[fg];[0:v][fg]overlay\"",
                    "-c:a copy",
                ]
            else:
                args = [
                    f"-i {input_file}",
                    f"-vf \"chromakey={color}:{similarity}:{blend}\"",
                    "-c:a copy",
                ]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_overlay":
            main = params["main_input"]
            overlay = params["overlay_input"]
            x = params.get("x", "0")
            y = params.get("y", "0")
            scale_w = params.get("scale_width", -1)
            opacity = params.get("opacity", 1.0)
            enable = params.get("enable_time")

            filter_parts = []
            if scale_w > 0:
                filter_parts.append(f"[1:v]scale={scale_w}:-1")
                if opacity < 1.0:
                    filter_parts.append(f",format=rgba,colorchannelmixer=aa={opacity}")
                filter_parts.append("[ovr]")
            else:
                if opacity < 1.0:
                    filter_parts.append(f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[ovr]")
                else:
                    filter_parts.append("[1:v]copy[ovr]")

            overlay_cmd = f"[0:v][ovr]overlay={x}:{y}"
            if enable:
                overlay_cmd += f":enable='{enable}'"

            fc = ";".join(["".join(filter_parts), overlay_cmd])
            args = [
                f"-i {main} -i {overlay}",
                f"-filter_complex \"{fc}\"",
                "-c:a copy",
            ]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_drawtext":
            input_file = params["input_file"]
            text = params["text"].replace("'", "'\\''").replace(":", "\\:")
            fontsize = params.get("fontsize", 48)
            fontcolor = params.get("fontcolor", "white")
            x = params.get("x", "(w-text_w)/2")
            y = params.get("y", "(h-text_h)/2")
            box = params.get("box", False)
            boxcolor = params.get("boxcolor", "black@0.5")
            boxborderw = params.get("boxborderw", 10)
            enable = params.get("enable")
            fontfile = params.get("fontfile")
            shadowcolor = params.get("shadowcolor")
            shadowx = params.get("shadowx", 2)
            shadowy = params.get("shadowy", 2)

            dt_parts = [f"text='{text}'", f"fontsize={fontsize}", f"fontcolor={fontcolor}",
                        f"x={x}", f"y={y}"]
            if fontfile:
                dt_parts.append(f"fontfile={fontfile}")
            if box:
                dt_parts.extend(["box=1", f"boxcolor={boxcolor}", f"boxborderw={boxborderw}"])
            if enable:
                dt_parts.append(f"enable='{enable}'")
            if shadowcolor:
                dt_parts.extend([f"shadowcolor={shadowcolor}", f"shadowx={shadowx}", f"shadowy={shadowy}"])

            dt_filter = "drawtext=" + ":".join(dt_parts)
            args = [f"-i {input_file}", f"-vf \"{dt_filter}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_scale":
            input_file = params["input_file"]
            w = params.get("width", 1920)
            h = params.get("height", 1080)
            pad = params.get("pad", False)
            pad_color = params.get("pad_color", "black")

            if pad:
                vf = (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{pad_color}"
                )
            else:
                vf = f"scale={w}:{h}"
            args = [f"-i {input_file}", f"-vf \"{vf}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_crop":
            input_file = params["input_file"]
            w = params["width"]
            h = params["height"]
            x = params.get("x", "(in_w-ow)/2")
            y = params.get("y", "(in_h-oh)/2")
            args = [f"-i {input_file}", f"-vf \"crop={w}:{h}:{x}:{y}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_speed":
            input_file = params["input_file"]
            speed = params.get("speed", 2.0)
            adjust_audio = params.get("adjust_audio", True)

            pts_factor = 1.0 / speed
            vf = f"setpts={pts_factor:.4f}*PTS"

            if adjust_audio and speed > 0:
                # atempo only supports 0.5-2.0, chain for larger values.
                atempo_parts = []
                remaining = speed
                while remaining > 2.0:
                    atempo_parts.append("atempo=2.0")
                    remaining /= 2.0
                while remaining < 0.5:
                    atempo_parts.append("atempo=0.5")
                    remaining /= 0.5
                atempo_parts.append(f"atempo={remaining:.4f}")
                af = ",".join(atempo_parts)
                args = [f"-i {input_file}", f"-vf \"{vf}\"", f"-af \"{af}\""]
            else:
                args = [f"-i {input_file}", f"-vf \"{vf}\"", "-an"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_reverse":
            input_file = params["input_file"]
            reverse_audio = params.get("reverse_audio", True)
            af = "-af areverse" if reverse_audio else ""
            args = [f"-i {input_file}", "-vf reverse", af]
            return self.executor.run_ffmpeg([a for a in args if a], output)

        elif name == "ffmpeg_loop":
            input_file = params["input_file"]
            count = params.get("count", 3)
            args = [f"-stream_loop {count} -i {input_file}", "-c copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_trim":
            input_file = params["input_file"]
            start = params.get("start", "00:00:00")
            end = params.get("end")
            duration = params.get("duration")
            copy = params.get("copy_codec", True)

            args = [f"-ss {start} -i {input_file}"]
            if end:
                args.append(f"-to {end}")
            elif duration:
                args.append(f"-t {duration}")
            args.append("-c copy" if copy else "-c:v libx264 -c:a aac")
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_concat":
            inputs = params["inputs"]
            method = params.get("method", "demuxer")

            if method == "demuxer":
                # Write a concat file list.
                list_path = self.executor.work_dir / "_concat_list.txt"
                with open(list_path, "w") as f:
                    for inp in inputs:
                        resolved = self.executor.validate_path(inp)
                        f.write(f"file '{resolved}'\n")
                args = [f"-f concat -safe 0 -i {list_path}", "-c copy"]
            else:
                # Filter-based concat.
                input_args = " ".join(f"-i {inp}" for inp in inputs)
                n = len(inputs)
                streams = "".join(f"[{i}:v][{i}:a]" for i in range(n))
                fc = f"\"{streams}concat=n={n}:v=1:a=1[v][a]\""
                args = [input_args, f"-filter_complex {fc}",
                        "-map \"[v]\" -map \"[a]\""]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_crossfade":
            clip_a = params["clip_a"]
            clip_b = params["clip_b"]
            transition = params.get("transition", "fade")
            dur = params.get("duration", 1.0)
            offset = params.get("offset")

            # If offset not given, try to calculate from clip_a duration.
            if offset is None:
                probe = self.executor.run(
                    f"ffprobe -v quiet -print_format json -show_format {clip_a}",
                    description="Get clip_a duration",
                )
                try:
                    clip_a_dur = float(json.loads(probe["stdout"])["format"]["duration"])
                    offset = max(0, clip_a_dur - dur)
                except (json.JSONDecodeError, KeyError):
                    offset = 4

            fc = (
                f"[0:v][1:v]xfade=transition={transition}:duration={dur}:offset={offset}[v];"
                f"[0:a][1:a]acrossfade=d={dur}[a]"
            )
            args = [
                f"-i {clip_a} -i {clip_b}",
                f"-filter_complex \"{fc}\"",
                "-map \"[v]\" -map \"[a]\" -c:v libx264 -pix_fmt yuv420p -c:a aac",
            ]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_fade":
            input_file = params["input_file"]
            fade_type = params.get("type", "both")
            dur = params.get("duration", 2.0)
            start = params.get("start_time", 0)
            fade_audio = params.get("fade_audio", True)
            color = params.get("color", "black")

            vf_parts = []
            af_parts = []
            if fade_type in ("in", "both"):
                vf_parts.append(f"fade=t=in:st=0:d={dur}:color={color}")
                if fade_audio:
                    af_parts.append(f"afade=t=in:st=0:d={dur}")
            if fade_type in ("out", "both"):
                vf_parts.append(f"fade=t=out:st={start}:d={dur}:color={color}")
                if fade_audio:
                    af_parts.append(f"afade=t=out:st={start}:d={dur}")

            vf = ",".join(vf_parts) if vf_parts else None
            af = ",".join(af_parts) if af_parts else None

            args = [f"-i {input_file}"]
            if vf:
                args.append(f"-vf \"{vf}\"")
            if af:
                args.append(f"-af \"{af}\"")
            else:
                args.append("-c:a copy")
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_blur_region":
            input_file = params["input_file"]
            x = params["x"]
            y = params["y"]
            w = params["width"]
            h = params["height"]
            strength = params.get("blur_strength", 20)
            enable = params.get("enable")

            fc = (
                f"split[main][blur];"
                f"[blur]crop={w}:{h}:{x}:{y},boxblur={strength}[blurred];"
                f"[main][blurred]overlay={x}:{y}"
            )
            if enable:
                fc = fc.rstrip('"') + f":enable='{enable}'"

            args = [f"-i {input_file}", f"-vf \"{fc}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_stabilize":
            input_file = params["input_file"]
            shakiness = params.get("shakiness", 5)
            smoothing = params.get("smoothing", 10)

            # Two-pass stabilization.
            transforms = self.executor.work_dir / "transforms.trf"
            self.executor.run(
                f"ffmpeg -y -i {input_file} -vf vidstabdetect=shakiness={shakiness}:result={transforms} -f null -",
                description="Stabilize pass 1: detect motion",
            )
            args = [f"-i {input_file}", f"-vf vidstabtransform=smoothing={smoothing}:input={transforms}"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_denoise":
            input_file = params["input_file"]
            method = params.get("method", "hqdn3d")
            strength = params.get("strength", 4)

            if method == "nlmeans":
                vf = f"nlmeans=s={strength}:p=7:r=5"
            else:
                vf = f"hqdn3d={strength}:{strength - 1}:{strength + 2}:{strength + 0.5}"
            args = [f"-i {input_file}", f"-vf \"{vf}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_eq":
            input_file = params["input_file"]
            b = params.get("brightness", 0)
            c = params.get("contrast", 1.0)
            s = params.get("saturation", 1.0)
            g = params.get("gamma", 1.0)
            gr = params.get("gamma_r", 1.0)
            gg = params.get("gamma_g", 1.0)
            gb = params.get("gamma_b", 1.0)
            vf = f"eq=brightness={b}:contrast={c}:saturation={s}:gamma={g}:gamma_r={gr}:gamma_g={gg}:gamma_b={gb}"
            args = [f"-i {input_file}", f"-vf \"{vf}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_extract_frames":
            input_file = params["input_file"]
            out_pattern = params.get("output_pattern", "frames/frame_%04d.png")
            fps = params.get("fps", 1)
            start = params.get("start_time")
            duration = params.get("duration")
            max_frames = params.get("max_frames", 0)

            # Ensure output dir exists.
            out_dir = (self.executor.work_dir / out_pattern).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            args = []
            if start:
                args.append(f"-ss {start}")
            args.append(f"-i {input_file}")
            if duration:
                args.append(f"-t {duration}")
            if fps > 0:
                args.append(f"-vf fps={fps}")
            if max_frames > 0:
                args.append(f"-frames:v {max_frames}")
            return self.executor.run_ffmpeg(args, out_pattern)

        elif name == "ffmpeg_create_video_from_images":
            pattern = params["input_pattern"]
            framerate = params.get("framerate", 30)
            audio = params.get("audio_file")
            codec = params.get("codec", "libx264")
            pix_fmt = params.get("pixel_format", "yuv420p")

            args = [f"-framerate {framerate} -i {pattern}"]
            if audio:
                args.append(f"-i {audio}")
            args.append(f"-c:v {codec} -pix_fmt {pix_fmt}")
            if audio:
                args.append("-shortest")
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_gif":
            input_file = params["input_file"]
            fps = params.get("fps", 15)
            w = params.get("width", 480)
            start = params.get("start")
            duration = params.get("duration")
            hq = params.get("high_quality", True)

            args = []
            if start:
                args.append(f"-ss {start}")
            args.append(f"-i {input_file}")
            if duration:
                args.append(f"-t {duration}")

            if hq:
                vf = (
                    f"fps={fps},scale={w}:-1:flags=lanczos,"
                    f"split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
                )
            else:
                vf = f"fps={fps},scale={w}:-1"

            args.append(f"-vf \"{vf}\"")
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_zoom_pan":
            input_image = params["input_image"]
            dur = params.get("duration", 5)
            z_start = params.get("zoom_start", 1.0)
            z_end = params.get("zoom_end", 1.5)
            pan = params.get("pan_direction", "none")
            w = params.get("width", 1920)
            h = params.get("height", 1080)
            fps = params.get("fps", 30)
            total_frames = int(dur * fps)

            # Compute zoom expression.
            zoom_rate = (z_end - z_start) / total_frames
            zoom_expr = f"min(zoom+{zoom_rate:.6f},{z_end})" if z_end > z_start else f"max(zoom-{abs(zoom_rate):.6f},{z_end})"

            # Pan expressions.
            if pan == "left":
                x_expr = "max(0,iw-iw/zoom-on*2)"
                y_expr = "ih/2-(ih/zoom/2)"
            elif pan == "right":
                x_expr = "min(iw-iw/zoom,on*2)"
                y_expr = "ih/2-(ih/zoom/2)"
            elif pan == "up":
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "max(0,ih-ih/zoom-on*2)"
            elif pan == "down":
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "min(ih-ih/zoom,on*2)"
            else:
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "ih/2-(ih/zoom/2)"

            vf = (
                f"scale=8000:-1,zoompan=z='{zoom_expr}':d={total_frames}:"
                f"x='{x_expr}':y='{y_expr}':s={w}x{h}:fps={fps}"
            )
            args = [f"-loop 1 -i {input_image}", f"-vf \"{vf}\"",
                    f"-t {dur} -c:v libx264 -pix_fmt yuv420p"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_split_screen":
            left = params["left_or_top"]
            right = params["right_or_bottom"]
            layout = params.get("layout", "horizontal")
            w = params.get("width", 1920)
            h = params.get("height", 1080)

            if layout == "horizontal":
                half = w // 2
                fc = (
                    f"[0:v]scale={half}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={half}:{h}:(ow-iw)/2:(oh-ih)/2[l];"
                    f"[1:v]scale={half}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={half}:{h}:(ow-iw)/2:(oh-ih)/2[r];"
                    f"[l][r]hstack=inputs=2"
                )
            else:
                half = h // 2
                fc = (
                    f"[0:v]scale={w}:{half}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{half}:(ow-iw)/2:(oh-ih)/2[t];"
                    f"[1:v]scale={w}:{half}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{half}:(ow-iw)/2:(oh-ih)/2[b];"
                    f"[t][b]vstack=inputs=2"
                )
            args = [f"-i {left} -i {right}", f"-filter_complex \"{fc}\"",
                    "-c:v libx264 -pix_fmt yuv420p -c:a aac -shortest"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_thumbnail_sheet":
            input_file = params["input_file"]
            cols = params.get("columns", 5)
            rows = params.get("rows", 4)
            tw = params.get("thumb_width", 320)
            th = params.get("thumb_height", 180)
            total = cols * rows

            # Calculate frame step.
            probe = self.executor.run(
                f"ffprobe -v quiet -print_format json -show_format {input_file}",
                description="Get duration for thumbnail sheet",
            )
            try:
                dur = float(json.loads(probe["stdout"])["format"]["duration"])
                frame_step = max(1, int(dur * 30 / total))  # Assuming ~30fps.
            except (json.JSONDecodeError, KeyError):
                frame_step = 30

            vf = f"select='not(mod(n,{frame_step}))',scale={tw}:{th},tile={cols}x{rows}"
            args = [f"-i {input_file}", f"-vf \"{vf}\"", "-frames:v 1"]
            return self.executor.run_ffmpeg(args, output)

        # --- Audio tools ---
        elif name == "ffmpeg_audio_normalize":
            input_file = params["input_file"]
            lufs = params.get("target_lufs", -14)
            tp = params.get("true_peak", -1)
            lra = params.get("lra", 11)
            args = [f"-i {input_file}", f"-af loudnorm=I={lufs}:TP={tp}:LRA={lra}", "-c:v copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_compress":
            input_file = params["input_file"]
            threshold = params.get("threshold_db", -20)
            ratio = params.get("ratio", 4)
            attack = params.get("attack_ms", 5)
            release = params.get("release_ms", 50)
            makeup = params.get("makeup_db", 0)
            af = f"acompressor=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}:makeup={makeup}dB"
            args = [f"-i {input_file}", f"-af \"{af}\"", "-c:v copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_eq":
            input_file = params["input_file"]
            bands = params.get("bands", [])
            eq_parts = []
            for band in bands:
                freq = band["frequency"]
                gain = band["gain"]
                width = band.get("width", 200)
                eq_parts.append(f"equalizer=f={freq}:t=h:w={width}:g={gain}")
            af = ",".join(eq_parts)
            args = [f"-i {input_file}", f"-af \"{af}\"", "-c:v copy"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_mix":
            inputs = params.get("inputs", [])
            duration = params.get("duration_mode", "first")
            n = len(inputs)

            input_args = " ".join(f"-i {inp['file']}" for inp in inputs)
            vol_parts = []
            for i, inp in enumerate(inputs):
                vol = inp.get("volume", 1.0)
                vol_parts.append(f"[{i}:a]volume={vol}[a{i}]")
            mix_inputs = "".join(f"[a{i}]" for i in range(n))
            fc = ";".join(vol_parts) + f";{mix_inputs}amix=inputs={n}:duration={duration}"
            args = [input_args, f"-filter_complex \"{fc}\""]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_duck":
            voice = params["voiceover"]
            music = params["music"]
            duck_db = params.get("duck_amount_db", -15)
            attack = params.get("attack_ms", 200)
            release = params.get("release_ms", 1000)

            music_vol = 10 ** (duck_db / 20)
            fc = (
                f"[1:a]volume={music_vol:.4f}[m];"
                f"[m][0:a]sidechaincompress=threshold=0.02:ratio=6:"
                f"attack={attack}:release={release}:level_sc=1[ducked];"
                f"[0:a][ducked]amix=inputs=2:duration=first"
            )
            args = [f"-i {voice} -i {music}", f"-filter_complex \"{fc}\""]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_fade":
            input_file = params["input_file"]
            fade_type = params.get("type", "both")
            dur = params.get("duration", 3.0)
            start = params.get("start_time")

            af_parts = []
            if fade_type in ("in", "both"):
                af_parts.append(f"afade=t=in:st=0:d={dur}")
            if fade_type in ("out", "both"):
                st = start if start is not None else 0
                af_parts.append(f"afade=t=out:st={st}:d={dur}")
            af = ",".join(af_parts)
            args = [f"-i {input_file}", f"-af \"{af}\""]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_audio_extract":
            input_file = params["input_file"]
            codec = params.get("codec", "copy")
            sr = params.get("sample_rate", 44100)
            bitrate = params.get("bitrate", "192k")

            if codec == "copy":
                args = [f"-i {input_file}", "-vn -acodec copy"]
            else:
                args = [f"-i {input_file}", f"-vn -ar {sr} -ac 2 -c:a {codec} -b:a {bitrate}"]
            return self.executor.run_ffmpeg(args, output)

        elif name == "ffmpeg_vignette":
            input_file = params["input_file"]
            angle = params.get("angle", "PI/4")
            args = [f"-i {input_file}", f"-vf \"vignette={angle}\"", "-c:a copy"]
            return self.executor.run_ffmpeg(args, output)

        return {"error": f"Unhandled FFmpeg tool: {name}"}

    def _execute_sox(self, name: str, params: dict) -> dict:
        """Build and execute a SoX command."""
        output = params.get("output", "output.wav")

        if name == "sox_normalize":
            input_file = params["input_file"]
            level = params.get("level_db", -1)
            return self.executor.run_sox([input_file, "norm", str(level)], output)

        elif name == "sox_trim":
            input_file = params["input_file"]
            start = params.get("start", 0)
            dur = params.get("duration", 0)
            args = [input_file, "trim", str(start)]
            if dur > 0:
                args.append(str(dur))
            return self.executor.run_sox(args, output)

        elif name == "sox_fade":
            input_file = params["input_file"]
            fade_in = params.get("fade_in", 0)
            fade_out = params.get("fade_out", 0)
            fade_type = params.get("fade_type", "t")
            args = [input_file, "fade", fade_type, str(fade_in), "0", str(fade_out)]
            return self.executor.run_sox(args, output)

        elif name == "sox_reverb":
            input_file = params["input_file"]
            reverberance = params.get("reverberance", 50)
            hf = params.get("hf_damping", 50)
            room = params.get("room_scale", 100)
            stereo = params.get("stereo_depth", 100)
            wet = params.get("wet_only", False)
            args = [input_file, "reverb"]
            if wet:
                args.append("-w")
            args.extend([str(reverberance), str(hf), str(room), str(stereo), "0", "0"])
            return self.executor.run_sox(args, output)

        elif name == "sox_echo":
            input_file = params["input_file"]
            gain_in = params.get("gain_in", 0.8)
            gain_out = params.get("gain_out", 0.88)
            delays = params.get("delays", [{"delay_ms": 60, "decay": 0.4}])
            args = [input_file, "echo", str(gain_in), str(gain_out)]
            for d in delays:
                args.extend([str(d["delay_ms"]), str(d["decay"])])
            return self.executor.run_sox(args, output)

        elif name == "sox_compand":
            input_file = params["input_file"]
            ad = params.get("attack_decay", "0.3,1")
            tf = params.get("transfer_function", "6:-70,-60,-20")
            gain = params.get("gain_db", -5)
            init = params.get("initial_level_db", -90)
            delay = params.get("delay", 0.2)
            args = [input_file, "compand", ad, tf, str(gain), str(init), str(delay)]
            return self.executor.run_sox(args, output)

        elif name == "sox_equalizer":
            input_file = params["input_file"]
            bands = params.get("bands", [])
            args = [input_file]
            for band in bands:
                freq = band["frequency"]
                q = band.get("q", 1.0)
                gain = band["gain_db"]
                args.extend(["equalizer", str(freq), f"{q}q", str(gain)])
            return self.executor.run_sox(args, output)

        elif name == "sox_bass":
            input_file = params["input_file"]
            gain = params.get("gain_db", 6)
            freq = params.get("frequency", 100)
            args = [input_file, "bass", str(gain), str(freq)]
            return self.executor.run_sox(args, output)

        elif name == "sox_treble":
            input_file = params["input_file"]
            gain = params.get("gain_db", 4)
            freq = params.get("frequency", 3000)
            args = [input_file, "treble", str(gain), str(freq)]
            return self.executor.run_sox(args, output)

        elif name == "sox_speed":
            input_file = params["input_file"]
            factor = params.get("factor", 1.5)
            args = [input_file, "tempo", str(factor)]
            return self.executor.run_sox(args, output)

        elif name == "sox_pitch":
            input_file = params["input_file"]
            cents = params.get("cents", 200)
            args = [input_file, "pitch", str(cents)]
            return self.executor.run_sox(args, output)

        elif name == "sox_noise_profile":
            input_file = params["input_file"]
            out_profile = params["output_profile"]
            start = params.get("start", 0)
            dur = params.get("duration", 0.5)
            resolved_profile = self.executor.validate_path(out_profile)
            cmd = f"sox {input_file} -n trim {start} {dur} noiseprof {resolved_profile}"
            return self.executor.run(cmd, description="Create noise profile")

        elif name == "sox_noise_reduce":
            input_file = params["input_file"]
            profile = params["noise_profile"]
            amount = params.get("amount", 0.21)
            args = [input_file, "noisered", profile, str(amount)]
            return self.executor.run_sox(args, output)

        elif name == "sox_silence_remove":
            input_file = params["input_file"]
            threshold = params.get("threshold", "1%")
            min_dur = params.get("min_duration", 0.1)
            args = [input_file, "silence", "1", str(min_dur), threshold, "-1", str(min_dur), threshold]
            return self.executor.run_sox(args, output)

        elif name == "sox_mix":
            inputs = params.get("inputs", [])
            mix_args = ["-m"]
            for inp in inputs:
                vol = inp.get("volume", 1.0)
                if vol != 1.0:
                    mix_args.extend(["-v", str(vol)])
                mix_args.append(inp["file"])
            return self.executor.run_sox(mix_args, output)

        elif name == "sox_stats":
            input_file = params["input_file"]
            return self.executor.run(
                f"sox {input_file} -n stat",
                description="Get audio statistics",
            )

        elif name == "sox_spectrogram":
            input_file = params["input_file"]
            title = params.get("title", "Spectrogram")
            w = params.get("width", 800)
            h = params.get("height", 400)
            resolved_out = self.executor.validate_path(output)
            return self.executor.run(
                f"sox {input_file} -n spectrogram -o {resolved_out} "
                f"-t '{title}' -x {w} -y {h}",
                description="Generate spectrogram",
            )

        return {"error": f"Unhandled SoX tool: {name}"}

    # ------------------------------------------------------------------
    # File operation tools
    # ------------------------------------------------------------------

    def _list_files(self, params: dict) -> dict:
        """List files in the work directory."""
        subdir = params.get("path", "")
        pattern = params.get("pattern", "*")

        target = self.executor.work_dir / subdir if subdir else self.executor.work_dir
        if not target.exists():
            return {"error": f"Directory does not exist: {subdir}"}

        files = []
        for p in sorted(target.glob(pattern)):
            if p.is_file():
                stat = p.stat()
                files.append({
                    "name": p.name,
                    "path": str(p.relative_to(self.executor.work_dir)),
                    "size_bytes": stat.st_size,
                    "size_human": _human_size(stat.st_size),
                })
        return {"files": files, "count": len(files)}

    def _copy_file(self, params: dict) -> dict:
        """Copy a file within the work directory."""
        src = self.executor.validate_path(params["source"])
        dst = self.executor.validate_path(params["destination"])
        if not src.exists():
            return {"error": f"Source does not exist: {params['source']}"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return {"success": True, "destination": str(dst.relative_to(self.executor.work_dir))}

    def _file_info(self, params: dict) -> dict:
        """Get file info."""
        path = self.executor.validate_path(params["path"])
        if not path.exists():
            return {"error": f"File does not exist: {params['path']}"}
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path.relative_to(self.executor.work_dir)),
            "size_bytes": stat.st_size,
            "size_human": _human_size(stat.st_size),
            "extension": path.suffix,
            "exists": True,
        }

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _build_tools(self) -> list[dict]:
        """Build tool definitions for the Anthropic API."""
        return get_all_power_tools()

    def _build_system_prompt(self, input_files: dict[str, Path]) -> str:
        """Build the system prompt with context about inputs and installed tools."""
        # Describe input files.
        if input_files:
            lines = []
            for name, path in input_files.items():
                rel = path.relative_to(self.executor.work_dir) if str(path).startswith(str(self.executor.work_dir)) else path
                size = _human_size(path.stat().st_size) if path.exists() else "missing"
                lines.append(f"- **{name}**: `{rel}` ({size})")
            input_desc = "\n".join(lines)
        else:
            input_desc = "No input files provided. Create everything from scratch."

        # Describe installed tools.
        installed = get_installed_tools()
        if installed:
            tool_lines = [f"- {info['label']} ({tool}): {info['version'][:60]}"
                          for tool, info in installed.items()]
            tools_desc = "\n".join(tool_lines)
        else:
            tools_desc = "No tools detected. Only Python/Pillow operations are available."

        return POWER_TOOLS_SYSTEM_PROMPT.format(
            input_files_description=input_desc,
            installed_tools_description=tools_desc,
        )

    def _prepare_inputs(self, input_files: dict[str, Path]) -> dict[str, Path]:
        """Prepare input files by symlinking/copying them into the work directory."""
        prepared: dict[str, Path] = {}
        for name, path in input_files.items():
            path = Path(path).resolve()
            if not path.exists():
                logger.warning("Input file does not exist: %s (%s)", name, path)
                continue

            # If already in work_dir, use as-is.
            if str(path).startswith(str(self.executor.work_dir)):
                prepared[name] = path
                continue

            # Copy into work_dir with a descriptive name.
            dest = self.executor.work_dir / f"input_{name}{path.suffix}"
            if not dest.exists():
                shutil.copy2(str(path), str(dest))
            prepared[name] = dest

        return prepared

    def _discover_outputs(self, known: dict[str, Path]) -> dict[str, Path]:
        """Discover output files in the work directory.

        Includes explicitly tracked outputs plus any new files that weren't
        part of the inputs.
        """
        # Start with known outputs.
        outputs = dict(known)

        # Look for common output patterns.
        for pattern in ["*.mp4", "*.mov", "*.png", "*.jpg", "*.gif",
                        "*.mp3", "*.wav", "*.aac", "*.webm"]:
            for f in self.executor.work_dir.glob(pattern):
                # Skip temp files.
                if f.name.startswith("_"):
                    continue
                # Skip input files.
                if f.name.startswith("input_"):
                    continue
                if f.name not in outputs:
                    outputs[f.name] = f

        return outputs


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
