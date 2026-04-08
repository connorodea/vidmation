"""Configuration system for VIDMATION."""

from vidmation.config.profiles import ChannelProfile, load_profile
from vidmation.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "ChannelProfile", "load_profile"]
