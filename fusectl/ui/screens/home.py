from pathlib import Path

from rich.table import Table
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label

from fusectl.ui.widgets import Banner, InfoPanel


class HomeScreen(Vertical):

    DEFAULT_CSS = """
    #home-status-panel {
        margin: 0 0;
    }
    #home-credit {
        color: #6272a4;
        margin-top: 0;
        text-align: center;
        width: 100%;
    }
    #home-buttons { height: 3; margin-top: 0; align: center middle; }
    #home-start { background: #8be9fd; color: #282a36; text-style: bold; }
    #home-refresh { background: #6272a4; color: #f8f8f2; }
    #home-quit { background: #ff5555; color: #f8f8f2; }
    """

    def compose(self) -> ComposeResult:
        yield Banner()
        with Horizontal(id="status-row"):
            yield InfoPanel(title="Status do Sistema", id="home-status-panel")
        yield Label("Gerenciador de CFW para Nintendo Switch", id="home-credit")
        with Horizontal(id="home-buttons"):
            yield Button("Iniciar", id="home-start", variant="primary")
            yield Button("Atualizar", id="home-refresh")
            yield Button("Finalizar", id="home-quit")

    def refresh_status(
        self,
        pkg_version: str | None,
        sd_version: str | None,
        rcm_connected: bool,
        sd_paths: list[Path],
        free_gb: float | None = None,
    ) -> None:
        table = Table(show_header=False, show_edge=False, pad_edge=False)
        table.add_column("item", style="bold #f8f8f2", ratio=1)
        table.add_column("valor", ratio=1)

        if pkg_version:
            table.add_row("Pacote CFW", Text(pkg_version, style="bold #50fa7b"))
        else:
            table.add_row("Pacote CFW", Text("não detectado", style="#f1fa8c"))

        if sd_version:
            table.add_row("Versão no SD", Text(sd_version, style="bold #50fa7b"))
        else:
            table.add_row("Versão no SD", Text("não detectado", style="#f1fa8c"))

        if rcm_connected:
            table.add_row("Switch RCM", Text("* Conectado", style="bold #50fa7b"))
        else:
            table.add_row("Switch RCM", Text("* Desconectado", style="#ff5555"))

        if sd_paths:
            paths_str = ", ".join(str(p) for p in sd_paths)
            table.add_row("SD Card", Text(f"* {paths_str}", style="bold #50fa7b"))
        else:
            table.add_row("SD Card", Text("* não detectado", style="#f1fa8c"))

        if free_gb is not None:
            table.add_row("Espaço livre", Text(f"{free_gb:.1f} GB", style="bold #8be9fd"))

        panel = self.query_one("#home-status-panel", InfoPanel)
        panel.set_content(table)
