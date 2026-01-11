import subprocess
import asyncio
from typing import List, Dict

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Static, DataTable
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

# --- Global Configurations ---
# Fetching titles and IDs with a flat-playlist limit to maintain high performance
YTDL_CMD = ["yt-dlp", "--get-title", "--get-id", "--flat-playlist"]

class OnceTube(App):
    """
    ONCE-TUBE: A high-performance TUI for searching and playing YouTube videos.
    Optimized for low CPU usage and seamless media playback.
    """

    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("q", "quit_app", "Quit"),
        Binding("escape", "clear_search", "Clear Search"),
    ]
    
    CSS_PATH = "once_tube.tcss"
    
    # Internal state for video data and process management
    videos: List[Dict[str, str]] = []
    active_processes: List[subprocess.Popen] = []

    def compose(self) -> ComposeResult:
        """Create child widgets for the application."""
        yield Header()
        with Horizontal(id="app-grid"):
            # Sidebar: Search Input
            with Vertical(id="search-area"):
                yield Static("SEARCH VIDEOS", classes="section-title")
                yield Input(placeholder="Type here, Rel...", id="search-input")
                yield Button("Search", id="search-button")
            
            # Main Content: Results Table
            with Vertical(id="results-area"):
                yield Static("TWICE LIBRARY", classes="section-title")
                yield Static("Search results will appear here.", id="results-message")
                yield DataTable(id="video-table")

            # Sidebar: Player Controls
            with Vertical(id="controls-area"):
                yield Static("MEDIA PLAYER", classes="section-title")
                yield Button("▶ Play Video", id="play-video-button")
                yield Button("♬ Play Audio", id="play-audio-button")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize components on application startup."""
        table = self.query_one("#video-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("No", "Video Title")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events based on their IDs."""
        if event.button.id == "search-button":
            await self.action_perform_search()
        elif event.button.id == "play-video-button":
            await self.action_play_selected(mode="video")
        elif event.button.id == "play-audio-button":
            await self.action_play_selected(mode="audio")

    async def action_perform_search(self) -> None:
        """Asynchronously fetch search results from YouTube using yt-dlp."""
        search_query = self.query_one("#search-input", Input).value
        if not search_query:
            return

        msg_widget = self.query_one("#results-message", Static)
        msg_widget.update("[magenta]Searching YouTube...[/magenta]")
        
        try:
            # Limits search to top 15 results for optimal responsiveness
            cmd = YTDL_CMD + [f"ytsearch15:{search_query}"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            result = stdout.decode().splitlines()
            self.videos = []
            
            # Parsing yt-dlp output (Title followed by ID)
            for i in range(0, len(result), 2):
                if i + 1 < len(result):
                    self.videos.append({"title": result[i], "id": result[i+1]})

            if not self.videos:
                msg_widget.update("[red]No videos found.[/red]")
            else:
                msg_widget.update(f"[green]Found {len(self.videos)} videos.[/green]")
                self._update_results_table()

        except Exception as e:
            msg_widget.update(f"[red]Error: {str(e)}[/red]")

    def _update_results_table(self) -> None:
        """Update the DataTable with search results using batch processing."""
        table = self.query_one("#video-table", DataTable)
        table.clear()
        
        # Performance optimization: Use add_rows for bulk updates to minimize CPU overhead
        rows = [(str(idx), vid['title']) for idx, vid in enumerate(self.videos, 1)]
        table.add_rows(rows)

    async def action_play_selected(self, mode: str = "video") -> None:
        """Launch mpv for the selected video and manage process singleton."""
        table = self.query_one("#video-table", DataTable)
        row_index = table.cursor_row
        
        if row_index is None or not self.videos:
            return
        
        # Singleton process logic: Terminate existing player before launching a new one
        for proc in self.active_processes:
            if proc.poll() is None:
                proc.terminate()
        self.active_processes.clear()

        try:
            video = self.videos[row_index]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"
            
            # Configure mpv with hardware acceleration enabled
            cmd = ["mpv", "--no-terminal", "--hwdec=auto", video_url]
            if mode == "audio":
                cmd.append("--no-video")
            
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.active_processes.append(proc)
            
            self.query_one("#results-message", Static).update(f"[cyan]Playing:[/cyan] {video['title']}")
            
        except Exception:
            pass

    def action_clear_search(self) -> None:
        """Reset search input and clear the results table."""
        self.query_one("#search-input", Input).value = ""
        self.query_one("#video-table", DataTable).clear()
        self.videos = []

    def action_quit_app(self) -> None:
        """Exit the application."""
        self.exit()

    def on_unmount(self) -> None:
        """Ensure all child processes are terminated on exit."""
        for proc in self.active_processes:
            if proc.poll() is None:
                proc.terminate()

def main():
    """Main entry point for the application."""
    app = OnceTube()
    app.run()

if __name__ == "__main__":
    main()