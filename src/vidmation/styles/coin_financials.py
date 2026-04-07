"""TheCoinFinancials-style video generation.

Style characteristics (from frame-by-frame analysis):
- AI-generated oil painting / impressionist style images (NOT stock footage)
- Historical scenes: banking rooms, trains, desks with quills, government chambers
- Dark, moody, atmospheric lighting
- Ken Burns slow zoom/pan on each image
- 2-3 word subtitle groups
- White bold text with ONE keyword highlighted in YELLOW
- Sans-serif font (Montserrat Bold)
- Bottom center placement, no background box
- "Ai" watermark in top-left corner
"""

from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class CoinFinancialsStyle:
    """Configuration for TheCoinFinancials visual style."""
    
    # Image generation
    image_style: str = "oil painting, impressionist style, dramatic lighting, moody atmospheric, historical"
    image_provider: str = "dalle"  # or "replicate" for flux
    image_size: str = "1792x1024"  # Landscape for DALL-E
    images_per_section: int = 8  # More images = more visual variety
    
    # Ken Burns
    ken_burns_scale: float = 1.05  # 5% zoom
    ken_burns_speed: float = 0.05  # Very slow drift
    clip_duration: float = 5.0  # Seconds per image
    
    # Subtitle style
    subtitle_font: str = "Montserrat-Bold"
    subtitle_size: int = 42
    subtitle_words_per_group: int = 3  # 2-3 words at a time
    subtitle_color: str = "white"
    subtitle_highlight_color: str = "#FFD700"  # Gold/yellow for keyword
    subtitle_position: str = "bottom_center"
    subtitle_margin_bottom: int = 80
    
    # Color grade
    contrast: float = 1.06
    brightness: float = 0.008
    saturation: float = 1.1
    gamma: float = 0.96
    vignette: str = "PI/5"
    
    # Watermark
    watermark_text: str = "Ai"
    watermark_position: str = "top_left"
    watermark_opacity: float = 0.4
    
    # Audio
    voice: str = "onyx"  # Deep, authoritative
    music_volume_db: float = -14.0
    
    # Title cards
    title_bg: str = "#0a0a0a"
    title_color: str = "white"
    title_accent: str = "#FFD700"
    title_duration: float = 2.5


def generate_image_prompt(narration_text: str, topic: str, style: CoinFinancialsStyle) -> str:
    """Generate a DALL-E prompt for an oil painting matching the narration."""
    return (
        f"{style.image_style}, depicting a scene related to: {narration_text[:100]}. "
        f"Topic context: {topic}. "
        f"High detail, rich textures, museum quality, no text in image, "
        f"16:9 aspect ratio, cinematic composition"
    )


def get_keyword_for_highlight(words: list[str]) -> int:
    """Pick the most important word in a subtitle group to highlight yellow.
    
    Returns the index of the word to highlight.
    Prefers: nouns, numbers, action verbs, financial terms.
    """
    # Financial/important keywords get priority
    priority_words = {
        "money", "bank", "billion", "trillion", "million", "dollar", "wealth",
        "crash", "crisis", "collapse", "secret", "hidden", "power", "control",
        "federal", "reserve", "gold", "debt", "inflation", "economy", "market",
        "stock", "invest", "profit", "loss", "trade", "wall", "street",
        "government", "central", "tax", "system", "scheme", "fraud", "steal",
        "war", "risk", "dangerous", "warning", "collapse", "destroyed",
        "massive", "huge", "incredible", "shocking", "terrifying", "panic",
        "ai", "automated", "technology", "software", "algorithm", "data",
        "wholesaling", "property", "real", "estate", "deal", "contract",
    }
    
    # Check each word against priority list
    for i, word in enumerate(words):
        if word.lower().strip(".,!?") in priority_words:
            return i
    
    # Default: highlight the last word (usually most impactful in English)
    return len(words) - 1


