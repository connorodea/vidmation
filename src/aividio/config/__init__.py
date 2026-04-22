"""Configuration system for VIDMATION."""

from aividio.config.profiles import ChannelProfile, load_profile
from aividio.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "ChannelProfile", "load_profile"]
