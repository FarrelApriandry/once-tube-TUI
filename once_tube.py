import subprocess
import asyncio
from typing import List, Dict

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Static, DataTable
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

# --- Constants ---
# Kita batasi search ke 15 biar yt-dlp gak kelamaan nge-scrape
YTDL_CMD = ["yt-dlp", "--get-title", "--get-id", "--flat-playlist"]

class OnceTube(App):
    """A professional TUI for TWICE fans with optimized CPU usage."""

    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("q", "quit_app", "Quit"),
        Binding("escape", "clear_search", "Clear Search"),
    ]
    
    CSS_PATH = "once_tube.tcss"
    
    videos: List[Dict[str, str]] = []
    active_processes: List[subprocess.Popen] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app-grid"):
            with Vertical(id="search-area"):
                yield Static("SEARCH VIDEOS", classes="section-title") # Pakai class CSS
                yield Input(placeholder="Type here, Rel...", id="search-input")
                yield Button("Search", id="search-button")
            
            with Vertical(id="results-area"):
                yield Static("TWICE LIBRARY", classes="section-title") # Pakai class CSS
                yield Static("Search results will appear here.", id="results-message")
                yield DataTable(id="video-table")

            with Vertical(id="controls-area"):
                yield Static("MEDIA PLAYER", classes="section-title") # Pakai class CSS
                yield Button("▶ Play Video", id="play-video-button")
                yield Button("♬ Play Audio", id="play-audio-button")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#video-table", DataTable)
        table.cursor_type = "row" # Bikin seleksi lebih cakep
        table.add_columns("No", "Video Title")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-button":
            await self.action_perform_search()
        elif event.button.id == "play-video-button":
            await self.action_play_selected(mode="video")
        elif event.button.id == "play-audio-button":
            await self.action_play_selected(mode="audio")

    async def action_perform_search(self) -> None:
        search_query = self.query_one("#search-input", Input).value
        if not search_query:
            return

        msg_widget = self.query_one("#results-message", Static)
        msg_widget.update("[magenta]Searching YouTube...[/magenta]")
        
        try:
            # Gunakan limit search 15
            cmd = YTDL_CMD + [f"ytsearch15:{search_query}"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            result = stdout.decode().splitlines()
            self.videos = []
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
        table = self.query_one("#video-table", DataTable)
        table.clear()
        # OPTIMASI: Gunakan add_rows (plural) untuk batch update.
        # Ini krusial buat nurunin CPU usage!
        rows = [(str(idx), vid['title']) for idx, vid in enumerate(self.videos, 1)]
        table.add_rows(rows)

    async def action_play_selected(self, mode: str = "video") -> None:
        table = self.query_one("#video-table", DataTable)
        row_index = table.cursor_row
        
        if row_index is None or not self.videos:
            return
        
        # Singleton logic
        for proc in self.active_processes:
            if proc.poll() is None:
                proc.terminate()
        self.active_processes.clear()

        try:
            video = self.videos[row_index]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"
            
            # Tambahin --hwdec=auto biar MPV pake GPU lo, bukan CPU
            cmd = ["mpv", "--no-terminal", "--hwdec=auto", video_url]
            if mode == "audio":
                cmd.append("--no-video")
            
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.active_processes.append(proc)
            
            self.query_one("#results-message", Static).update(f"[cyan]Playing:[/cyan] {video['title']}")
            
        except Exception:
            pass

    def action_clear_search(self) -> None:
        self.query_one("#search-input", Input).value = ""
        self.query_one("#video-table", DataTable).clear()
        self.videos = []

    def action_quit_app(self) -> None:
        self.exit()

    def on_unmount(self) -> None:
        for proc in self.active_processes:
            if proc.poll() is None:
                proc.terminate()

def main():
    app = OnceTube()
    app.run()

if __name__ == "__main__":
    main()