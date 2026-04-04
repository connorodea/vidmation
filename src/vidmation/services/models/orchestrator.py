"""ModelOrchestrator — the multi-model brain that routes generation requests.

This is a key differentiator over platforms like InVideo.  Instead of using a
single model for everything, the orchestrator analyses each script section and
routes it to the best-suited model based on content type, budget, and
availability.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vidmation.config.settings import Settings, get_settings
from vidmation.services.videogen import create_video_generator
from vidmation.services.videogen.base import VideoGenerator

if TYPE_CHECKING:
    from vidmation.config.profiles import ChannelProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model aliases → (provider, model_id) for unified lookup
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    # Replicate models
    "minimax-video-01": ("replicate", "minimax/video-01-live"),
    "luma-ray": ("replicate", "luma/ray"),
    "hunyuan-video": ("replicate", "tencent/hunyuan-video"),
    "wan2.1": ("replicate", "wan-ai/wan2.1-t2v-14b"),
    # fal.ai models
    "kling-2.1": ("fal", "fal-ai/kling-video/v2.1/master"),
    "minimax-fal": ("fal", "fal-ai/minimax/video-01-live"),
    "hunyuan-fal": ("fal", "fal-ai/hunyuan-video"),
    "runway-gen3": ("fal", "fal-ai/runway-gen3/turbo"),
    # Local (free)
    "local": ("local", ""),
    "ken_burns": ("local", ""),
    "text_card": ("local", ""),
    "gradient": ("local", ""),
    "particles": ("local", ""),
}


class ModelOrchestrator:
    """Routes generation requests to the best model based on content type.

    The orchestrator maintains routing rules that map content categories to
    an ordered preference list of models.  When generating, it tries the
    first available model and falls back down the list.

    This enables:
    * **Quality optimisation** — cinematic shots get Kling/Runway, text cards
      use free local generation.
    * **Cost control** — cheaper models are preferred for bulk content.
    * **Resilience** — if an API is down, the next model is tried.
    """

    # Content category → ordered preference list of model aliases
    ROUTING_RULES: dict[str, list[str]] = {
        "cinematic": ["kling-2.1", "runway-gen3", "luma-ray", "minimax-video-01"],
        "product": ["minimax-video-01", "minimax-fal", "kling-2.1"],
        "nature": ["hunyuan-video", "luma-ray", "hunyuan-fal", "wan2.1"],
        "abstract": ["wan2.1", "hunyuan-video", "local"],
        "text_card": ["local"],
        "title_card": ["local"],
        "stat_card": ["local"],
        "quote_card": ["local"],
        "talking_head": ["kling-2.1", "runway-gen3", "minimax-video-01"],
        "action": ["runway-gen3", "kling-2.1", "minimax-video-01"],
        "explainer": ["minimax-video-01", "hunyuan-video", "local"],
        "transition": ["local", "wan2.1"],
        "default": ["minimax-video-01", "hunyuan-video", "local"],
    }

    def __init__(
        self,
        settings: Settings | None = None,
        preferred_provider: str | None = None,
        max_cost_per_video: float | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.preferred_provider = preferred_provider
        self.max_cost_per_video = max_cost_per_video
        self._generator_cache: dict[str, VideoGenerator] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_generator(self, model_alias: str) -> VideoGenerator:
        """Return a (cached) VideoGenerator for the given model alias."""
        if model_alias in self._generator_cache:
            return self._generator_cache[model_alias]

        registry_entry = MODEL_REGISTRY.get(model_alias)
        if registry_entry is None:
            raise ValueError(f"Unknown model alias: {model_alias!r}")

        provider, model_id = registry_entry
        kwargs: dict[str, Any] = {"provider": provider, "settings": self.settings}
        if model_id:
            kwargs["model_id"] = model_id

        generator = create_video_generator(**kwargs)
        self._generator_cache[model_alias] = generator
        return generator

    def _resolve_category(self, section: dict) -> str:
        """Determine the content category for a script section."""
        # Check explicit visual_type first
        visual_type = section.get("visual_type", "").lower()
        if visual_type in self.ROUTING_RULES:
            return visual_type

        # Map common visual_type values to categories
        type_mapping = {
            "ai_image": "cinematic",
            "ai_video": "cinematic",
            "stock_video": "default",
            "stock_image": "default",
            "b_roll": "cinematic",
            "talking_head": "talking_head",
            "screen_recording": "default",
            "text_overlay": "text_card",
            "quote": "quote_card",
            "statistic": "stat_card",
        }

        mapped = type_mapping.get(visual_type, "")
        if mapped:
            return mapped

        # Fall back to keyword analysis of the visual query / prompt
        query = section.get("visual_query", "").lower()
        if any(kw in query for kw in ("nature", "landscape", "ocean", "forest", "sunset")):
            return "nature"
        if any(kw in query for kw in ("product", "review", "unbox")):
            return "product"
        if any(kw in query for kw in ("title", "intro")):
            return "title_card"
        if any(kw in query for kw in ("abstract", "geometric", "pattern")):
            return "abstract"
        if any(kw in query for kw in ("action", "sport", "fast", "dynamic")):
            return "action"

        return "default"

    def _select_model(self, category: str) -> str:
        """Pick the best available model alias for a content category."""
        candidates = self.ROUTING_RULES.get(category, self.ROUTING_RULES["default"])

        # If a preferred provider is set, prioritise models from that provider
        if self.preferred_provider:
            preferred = [
                m for m in candidates
                if MODEL_REGISTRY.get(m, ("", ""))[0] == self.preferred_provider
            ]
            if preferred:
                return preferred[0]

        return candidates[0]

    def _generate_single(
        self,
        section: dict,
        output_dir: Path,
    ) -> dict[str, Any]:
        """Generate a video clip for a single section with fallback logic."""
        category = self._resolve_category(section)
        candidates = self.ROUTING_RULES.get(category, self.ROUTING_RULES["default"])
        section_idx = section.get("section_number", 0)

        prompt = section.get("visual_query", section.get("narration", ""))
        duration = float(section.get("duration", 5.0))
        image_path = section.get("source_image_path")

        output_path = output_dir / f"section_{section_idx:03d}.mp4"

        last_error: Exception | None = None

        for model_alias in candidates:
            try:
                generator = self._get_generator(model_alias)
                provider, model_id = MODEL_REGISTRY.get(model_alias, ("local", ""))

                logger.info(
                    "[orchestrator] Section %d: category=%s, model=%s (%s)",
                    section_idx,
                    category,
                    model_alias,
                    provider,
                )

                # Use image-to-video if we have a source image and the model supports it
                if image_path and Path(image_path).exists():
                    models_meta = generator.list_models()
                    current_model_meta = next(
                        (m for m in models_meta if m.get("supports_i2v")),
                        None,
                    )
                    if current_model_meta and current_model_meta.get("supports_i2v"):
                        result_path = generator.generate_from_image(
                            image_path=Path(image_path),
                            prompt=prompt,
                            duration=duration,
                            output_path=output_path,
                        )
                    else:
                        result_path = generator.generate(
                            prompt=prompt,
                            duration=duration,
                            output_path=output_path,
                        )
                else:
                    result_path = generator.generate(
                        prompt=prompt,
                        duration=duration,
                        output_path=output_path,
                    )

                return {
                    "path": str(result_path),
                    "section_index": section_idx,
                    "type": "ai_video",
                    "source": f"{provider}/{model_alias}",
                    "category": category,
                    "cost": generator.estimate_cost(duration, model_id or None),
                }

            except Exception as e:
                last_error = e
                logger.warning(
                    "[orchestrator] Section %d: model %s failed (%s), trying next...",
                    section_idx,
                    model_alias,
                    str(e),
                )
                continue

        # All models failed
        raise RuntimeError(
            f"All models failed for section {section_idx} "
            f"(category={category!r}): {last_error}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_for_section(
        self,
        section: dict,
        profile: ChannelProfile,
        output_dir: Path | None = None,
    ) -> Path:
        """Given a script section, pick the best model and generate a clip.

        Args:
            section: A script section dict with keys like ``visual_query``,
                ``visual_type``, ``duration``, ``section_number``.
            profile: The channel profile for style context.
            output_dir: Directory to save the generated clip.

        Returns:
            Path to the generated video clip.
        """
        if output_dir is None:
            output_dir = self.settings.output_dir / "ai_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self._generate_single(section, output_dir)
        return Path(result["path"])

    def generate_batch(
        self,
        sections: list[dict],
        profile: ChannelProfile,
        output_dir: Path | None = None,
        parallel: bool = True,
        max_workers: int = 3,
    ) -> list[dict]:
        """Generate video clips for all sections.

        Args:
            sections: List of script section dicts.
            profile: The channel profile for style context.
            output_dir: Directory to save the generated clips.
            parallel: Whether to generate clips in parallel.
            max_workers: Max parallel generations (to avoid API rate limits).

        Returns:
            List of result dicts with ``path``, ``section_index``, ``type``,
            ``source``, ``category``, and ``cost`` keys.
        """
        if output_dir is None:
            output_dir = self.settings.output_dir / "ai_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict] = []

        if not parallel or len(sections) <= 1:
            for section in sections:
                result = self._generate_single(section, output_dir)
                results.append(result)
            return sorted(results, key=lambda r: r["section_index"])

        # Parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_section = {
                executor.submit(self._generate_single, section, output_dir): section
                for section in sections
            }

            for future in as_completed(future_to_section):
                section = future_to_section[future]
                section_idx = section.get("section_number", "?")
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(
                        "[orchestrator] Section %s complete: %s",
                        section_idx,
                        result["source"],
                    )
                except Exception as e:
                    logger.error(
                        "[orchestrator] Section %s FAILED: %s",
                        section_idx,
                        str(e),
                    )
                    raise

        return sorted(results, key=lambda r: r["section_index"])

    def estimate_total_cost(self, sections: list[dict]) -> dict[str, Any]:
        """Return cost breakdown per section and total estimated cost.

        Args:
            sections: List of script section dicts.

        Returns:
            Dict with ``sections`` (list of per-section cost info) and
            ``total_usd`` (float).
        """
        section_costs: list[dict[str, Any]] = []
        total = 0.0

        for section in sections:
            category = self._resolve_category(section)
            model_alias = self._select_model(category)
            provider, model_id = MODEL_REGISTRY.get(model_alias, ("local", ""))
            duration = float(section.get("duration", 5.0))

            try:
                generator = self._get_generator(model_alias)
                cost = generator.estimate_cost(duration, model_id or None)
            except Exception:
                # If we can't instantiate the generator, estimate conservatively
                cost = duration * 0.05

            section_costs.append({
                "section_number": section.get("section_number", 0),
                "category": category,
                "model": model_alias,
                "provider": provider,
                "duration": duration,
                "estimated_cost_usd": round(cost, 4),
            })
            total += cost

        return {
            "sections": section_costs,
            "total_usd": round(total, 4),
            "model_count": len({s["model"] for s in section_costs}),
        }
