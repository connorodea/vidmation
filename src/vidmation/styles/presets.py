"""Dynamic style presets for any niche/topic.

The AI adapts image prompts, color grading, caption styles, voice selection,
and music mood based on the user's topic and chosen visual style.
"""

from dataclasses import dataclass, field

@dataclass
class VideoStyle:
    """A visual style preset that adapts to any topic."""
    id: str
    name: str
    description: str
    
    # Image generation
    image_prompt_prefix: str  # Prepended to every image prompt
    image_prompt_suffix: str  # Appended to every image prompt
    
    # Color grade (ffmpeg eq values)
    contrast: float = 1.05
    brightness: float = 0.008
    saturation: float = 1.1
    gamma: float = 0.96
    vignette: str = "PI/5"
    
    # Captions
    subtitle_color: str = "white"
    highlight_color: str = "#FFD700"  # Keyword highlight
    words_per_group: int = 3
    font_size: int = 40
    
    # Title cards
    title_bg: str = "#0a0a0a"
    title_accent: str = "#FFD700"
    
    # Voice recommendation
    recommended_voice: str = "onyx"
    
    # Music mood
    music_mood: str = "cinematic"


# ── STYLE PRESETS ──

STYLES = {
    "oil_painting": VideoStyle(
        id="oil_painting",
        name="Oil Painting",
        description="Museum-quality impressionist paintings. Perfect for history, finance, storytelling.",
        image_prompt_prefix="Oil painting, impressionist style, dramatic moody lighting, museum quality artwork, rich textures,",
        image_prompt_suffix="16:9 cinematic composition, no text in image, highly detailed brushwork",
        contrast=1.06, brightness=0.008, saturation=1.1, gamma=0.96,
        highlight_color="#FFD700",
        recommended_voice="onyx",
        music_mood="dark_cinematic",
    ),
    
    "cinematic_realism": VideoStyle(
        id="cinematic_realism",
        name="Cinematic Realism",
        description="Photorealistic cinematic scenes. Great for business, tech, lifestyle.",
        image_prompt_prefix="Cinematic photograph, photorealistic, dramatic lighting, shallow depth of field, film grain,",
        image_prompt_suffix="16:9 widescreen, professional cinematography, 4K quality, no text",
        contrast=1.08, brightness=0.01, saturation=1.05, gamma=0.95,
        highlight_color="#10a37f",
        title_accent="#10a37f",
        recommended_voice="echo",
        music_mood="upbeat_cinematic",
    ),
    
    "anime_illustration": VideoStyle(
        id="anime_illustration",
        name="Anime / Illustration",
        description="Stylized anime art. Perfect for storytelling, gaming, pop culture.",
        image_prompt_prefix="Anime illustration, highly detailed, vibrant colors, studio quality,",
        image_prompt_suffix="16:9 widescreen, dynamic composition, clean linework, no text",
        contrast=1.1, brightness=0.02, saturation=1.3, gamma=0.98,
        highlight_color="#FF6B6B",
        title_accent="#FF6B6B",
        recommended_voice="nova",
        music_mood="energetic",
    ),
    
    "watercolor": VideoStyle(
        id="watercolor",
        name="Watercolor",
        description="Soft, dreamy watercolor scenes. Ideal for wellness, spirituality, nature.",
        image_prompt_prefix="Watercolor painting, soft and dreamy, gentle lighting, ethereal atmosphere,",
        image_prompt_suffix="16:9 composition, delicate brushstrokes, pastel tones, no text",
        contrast=1.02, brightness=0.015, saturation=0.95, gamma=1.0,
        vignette="PI/7",
        highlight_color="#7C9FF5",
        title_accent="#7C9FF5",
        recommended_voice="shimmer",
        music_mood="ambient_calm",
    ),
    
    "dark_noir": VideoStyle(
        id="dark_noir",
        name="Dark Noir",
        description="High-contrast film noir. Perfect for crime, mystery, conspiracy, true crime.",
        image_prompt_prefix="Film noir style, high contrast black and white with selective color, dramatic shadows, moody,",
        image_prompt_suffix="16:9 cinematic, atmospheric, gritty detail, no text",
        contrast=1.15, brightness=-0.01, saturation=0.7, gamma=0.9,
        vignette="PI/4",
        highlight_color="#FF4444",
        title_accent="#FF4444",
        recommended_voice="onyx",
        music_mood="dark_suspense",
    ),
    
    "retro_vintage": VideoStyle(
        id="retro_vintage",
        name="Retro Vintage",
        description="70s/80s vintage aesthetic. Great for nostalgia, music, pop culture, history.",
        image_prompt_prefix="Retro vintage photograph, 1970s aesthetic, warm film tones, grain texture,",
        image_prompt_suffix="16:9 composition, authentic period feel, analog warmth, no text",
        contrast=1.05, brightness=0.02, saturation=1.2, gamma=0.93,
        highlight_color="#F5A623",
        title_accent="#F5A623",
        recommended_voice="fable",
        music_mood="retro_synth",
    ),
    
    "corporate_clean": VideoStyle(
        id="corporate_clean",
        name="Corporate Clean",
        description="Professional, minimal design. Business, SaaS, marketing, B2B content.",
        image_prompt_prefix="Clean professional photograph, modern office setting, bright natural lighting, minimal design,",
        image_prompt_suffix="16:9 composition, sharp focus, corporate style, no text, white space",
        contrast=1.03, brightness=0.015, saturation=1.0, gamma=1.0,
        vignette="PI/8",
        highlight_color="#10a37f",
        title_accent="#10a37f",
        recommended_voice="echo",
        music_mood="corporate_upbeat",
    ),
    
    "sci_fi_futuristic": VideoStyle(
        id="sci_fi_futuristic",
        name="Sci-Fi Futuristic",
        description="Neon-lit cyberpunk/sci-fi. AI, technology, future trends, space.",
        image_prompt_prefix="Futuristic sci-fi scene, neon lighting, cyberpunk aesthetic, holographic elements,",
        image_prompt_suffix="16:9 cinematic, dark with vibrant neon accents, highly detailed, no text",
        contrast=1.1, brightness=0.005, saturation=1.25, gamma=0.94,
        highlight_color="#00F5FF",
        title_accent="#00F5FF",
        recommended_voice="alloy",
        music_mood="electronic_ambient",
    ),
    
    "nature_documentary": VideoStyle(
        id="nature_documentary",
        name="Nature Documentary",
        description="BBC Earth quality nature scenes. Wildlife, environment, science, geography.",
        image_prompt_prefix="National Geographic style photograph, stunning nature scene, golden hour lighting, breathtaking,",
        image_prompt_suffix="16:9 landscape, ultra sharp, vivid natural colors, no text, professional wildlife photography",
        contrast=1.04, brightness=0.01, saturation=1.15, gamma=0.97,
        vignette="PI/6",
        highlight_color="#4CAF50",
        title_accent="#4CAF50",
        recommended_voice="nova",
        music_mood="orchestral_nature",
    ),
    
    "stock_footage": VideoStyle(
        id="stock_footage",
        name="Stock Footage",
        description="Real stock video clips from Pexels. Traditional B-roll style for any topic.",
        image_prompt_prefix="",  # Not used — uses Pexels video search instead
        image_prompt_suffix="",
        contrast=1.05, brightness=0.008, saturation=1.08, gamma=0.97,
        highlight_color="#FFFFFF",
        title_accent="#10a37f",
        recommended_voice="echo",
        music_mood="cinematic",
    ),
}


def get_style(style_id: str) -> VideoStyle:
    """Get a style preset by ID."""
    if style_id not in STYLES:
        raise ValueError(f"Unknown style: {style_id}. Available: {list(STYLES.keys())}")
    return STYLES[style_id]


def list_styles() -> list[dict]:
    """List all available style presets."""
    return [{"id": s.id, "name": s.name, "description": s.description} for s in STYLES.values()]


def build_image_prompt(topic_context: str, narration_text: str, style: VideoStyle) -> str:
    """Build a complete image generation prompt for any topic + style combination.
    
    The style provides the artistic direction, the topic/narration provides the content.
    This works for ANY niche — the AI adapts the scene to match what's being discussed.
    """
    if not style.image_prompt_prefix:
        return ""  # Stock footage style — no image generation needed
    
    return f"{style.image_prompt_prefix} depicting a scene related to: {narration_text[:100]}. Context: {topic_context[:50]}. {style.image_prompt_suffix}"


def get_ffmpeg_grade(style: VideoStyle) -> str:
    """Get the ffmpeg eq filter string for a style's color grade."""
    return (
        f"eq=contrast={style.contrast}:brightness={style.brightness}:"
        f"saturation={style.saturation}:gamma={style.gamma},"
        f"vignette={style.vignette}"
    )
