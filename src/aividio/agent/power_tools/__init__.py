"""Power Tools Agent -- CLI media manipulation sub-agent.

The PowerToolsAgent is delegated to by the main AgentOrchestrator when
advanced media transformation is required: compositing, text rendering,
color grading, audio processing, format conversion, and more.

It wraps CLI tools (ImageMagick, FFmpeg, SoX, etc.) behind a
Claude-powered reasoning layer that can chain commands together
intelligently.

Usage::

    from aividio.agent.power_tools import PowerToolsAgent

    agent = PowerToolsAgent()
    result = agent.execute_task(
        task="Create a cinematic title card with the text 'Top 10 Side Hustles'",
    )
    print(result["output_files"])
"""

from aividio.agent.power_tools.agent import PowerToolsAgent
from aividio.agent.power_tools.executors import CommandExecutor
from aividio.agent.power_tools.precheck import check_all_tools
from aividio.agent.power_tools.recipes import PowerToolRecipes

__all__ = [
    "PowerToolsAgent",
    "CommandExecutor",
    "PowerToolRecipes",
    "check_all_tools",
]
