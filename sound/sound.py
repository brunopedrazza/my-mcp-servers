import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sound")


def run_osascript(script: str) -> bool:
    """Run an AppleScript command with osascript."""
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        return True
    except Exception:
        return False


@mcp.tool()
async def play() -> str:
    """Play or resume the current track."""
    if run_osascript('tell application "Music" to play'):
        return "Playback started"
    return "Failed to start playback"


@mcp.tool()
async def pause() -> str:
    """Pause the current track."""
    if run_osascript('tell application "Music" to pause'):
        return "Playback paused"
    return "Failed to pause playback"


@mcp.tool()
async def next_track() -> str:
    """Skip to the next track."""
    if run_osascript('tell application "Music" to next track'):
        return "Skipped to next track"
    return "Failed to skip track"


@mcp.tool()
async def previous_track() -> str:
    """Return to the previous track."""
    if run_osascript('tell application "Music" to previous track'):
        return "Went to previous track"
    return "Failed to go to previous track"


if __name__ == "__main__":
    mcp.run(transport="stdio")
