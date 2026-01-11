from os import sync
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
    video_queue: List[Dict[str, str]] = []
    is_playing: bool = False
    is_paused: bool = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the application."""
        yield Header()
        with Horizontal(id="app-grid"):
            # Sidebar: Search Input
            with Vertical(id="search-area"):
                yield Static("SEARCH VIDEOS", classes="section-title")
                yield Input(placeholder="Type here...", id="search-input")
                yield Button("Search", id="search-button")
            
            # Main Content: Results Table
            with Vertical(id="results-area"):
                yield Static("TWICE LIBRARY", classes="section-title")
                yield Static("Search results will appear here.", id="results-message")
                yield DataTable(id="video-table")

            # Sidebar: Player Controls & Queue
            with Vertical(id="controls-area"):
                yield Static("MEDIA PLAYER", classes="section-title")
                yield Button("▶ Play Video", id="play-video-button")
                yield Button("♬ Play Audio", id="play-audio-button")
                yield Button("➕ Add to Queue", id="add-queue-button")
                
                yield Static("NEXT IN QUEUE", classes="section-title")
                yield DataTable(id="queue-table")

                with Horizontal(id="playback-controls"):
                    yield Button("⏸ Pause", id="pause-button")
                    yield Button("⏭ Next", id="next-button")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize components on application startup."""
        table = self.query_one("#video-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("No", "Video Title")

        queue_table = self.query_one("#queue-table", DataTable)
        queue_table.cursor_type = "row"
        queue_table.add_columns("No", "Queue Title")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-button":
            await self.action_perform_search()
        elif event.button.id == "play-video-button":
            await self.action_play_now(mode="video")
        elif event.button.id == "play-audio-button":
            await self.action_play_now(mode="audio")
        elif event.button.id == "add-queue-button":
            await self.action_add_to_queue()
        elif event.button.id == "pause-button":
            self.action_toggle_pause()
        elif event.button.id == "next-button":
            await self.action_skip_next()

    async def action_add_to_queue(self) -> None:
        table = self.query_one("#video-table", DataTable)
        row_index = table.cursor_row
        
        if row_index is not None and self.videos:
            video = self.videos[row_index].copy() # Copy biar aman
            # Default kita kasih audio, tapi lo bisa modif ini biar nanya atau 
            # ngikutin settingan global
            video["mode"] = "video" # Misal kita default-kan ke video
            
            self.video_queue.append(video)
            self._update_queue_table()

            if not self.is_playing:
                await self.play_next_in_queue()
        
    async def action_play_now(self, mode: str) -> None:
        """Fungsi buat muter lagu sekarang juga (Instan Play) tapi tetep dukung queue."""
        table = self.query_one("#video-table", DataTable)
        row_index = table.cursor_row
        
        if row_index is not None and self.videos:
            video = self.videos[row_index]
            # Set is_playing True biar queue otomatis ga nabrak
            self.is_playing = True
            await self.start_mpv_process(video, mode=mode)

    def action_toggle_pause(self) -> None:
        """Toggle pause/resume menggunakan sinyal OS."""
        import signal
        import os
        
        for proc in self.active_processes:
            if proc.returncode is None:
                try:
                    if not self.is_paused:
                        os.kill(proc.pid, signal.SIGSTOP) # Freeze proses
                        self.is_paused = True
                        self.query_one("#pause-button", Button).label = "▶ Resume"
                    else:
                        os.kill(proc.pid, signal.SIGCONT) # Jalanin lagi
                        self.is_paused = False
                        self.query_one("#pause-button", Button).label = "|| Pause"
                except Exception:
                    pass

    async def action_skip_next(self) -> None:
        """Bunuh proses, dan biarkan watcher memanggil lagu selanjutnya."""
        if not self.active_processes:
            return
            
        for proc in self.active_processes:
            if proc.returncode is None:
                proc.terminate()
        
        # Reset state pause kalo lagi pause
        self.is_paused = False
        self.query_one("#pause-button", Button).label = "⏸ Pause"
        self.query_one("#results-message", Static).update("[yellow]Skipping...[/yellow]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the Enter key press when the search input is focused."""
        if event.input.id == "search-input":
            await self.action_perform_search()

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

    def _update_queue_table(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        rows = [(str(idx), vid['title']) for idx, vid in enumerate(self.video_queue, 1)]
        table.add_rows(rows)

    async def play_next_in_queue(self) -> None:
        """Ambil lagu pertama di queue dan putar sesuai modenya."""
        if not self.video_queue:
            self.is_playing = False
            return

        self.is_playing = True
        video = self.video_queue.pop(0)
        self._update_queue_table()
        
        mode = video.get("mode", "video") 
        await self.start_mpv_process(video, mode=mode)

    async def start_mpv_process(self, video: Dict, mode: str = "audio") -> None:
        """Core function buat jalanin mpv dengan watcher."""
        video_url = f"https://www.youtube.com/watch?v={video['id']}"
        cmd = ["mpv", "--no-terminal", "--hwdec=auto", video_url]
        if mode == "audio":
            cmd.append("--no-video")

        self.query_one("#results-message", Static).update(f"[cyan]Now Playing:[/cyan] {video['title']}")

        # Bersihin proses lama
        for proc in self.active_processes:
            if proc.returncode is None:
                proc.terminate()
        self.active_processes.clear()

        # Pake ASYNC biar bisa di-wait
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        self.active_processes.append(proc)

        # WATCHER: Ini yang bikin Next dan Auto-play jalan
        async def wait_for_end():
            await proc.wait()
            # Kalo proses selesai (baik karena tamat atau di-terminate/skip)
            # Cek apakah ada antrean
            if self.video_queue:
                await self.play_next_in_queue()
            else:
                self.is_playing = False
                self.query_one("#results-message", Static).update("[yellow]Finished. Queue empty.[/yellow]")

        asyncio.create_task(wait_for_end())

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
            if proc.returncode is None: 
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass

def main():
    """Main entry point for the application."""
    app = OnceTube()
    app.run()

if __name__ == "__main__":
    main()