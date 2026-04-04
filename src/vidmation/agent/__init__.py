"""AI Agent Orchestrator — Claude-powered video production director.

The agent module provides an AI-driven orchestration layer that replaces the
rigid stage-based pipeline with an intelligent, adaptive workflow.  Claude
analyzes the video topic, creates a production plan, makes real-time decisions
about which services to use, handles errors by trying alternatives, and
optimises for quality, cost, and speed.

Usage::

    from vidmation.agent.orchestrator import AgentOrchestrator
    from vidmation.config.profiles import get_default_profile

    agent = AgentOrchestrator()
    ctx = agent.create_video(
        topic="10 Passive Income Ideas for 2025",
        channel_profile=get_default_profile(),
    )
    print(ctx.final_video_path)
"""

from vidmation.agent.orchestrator import AgentOrchestrator

__all__ = ["AgentOrchestrator"]
