from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, ProgressBar

from fusectl.ui.widgets import InfoPanel


class InstallScreen(Vertical):

    DEFAULT_CSS = """
    #install-summary {
        margin: 0 0;
    }
    #install-progress {
        margin: 0 0;
    }
    #install-progress-label {
        margin: 0 0;
        height: 1;
    }
    #install-status {
        margin: 0 0;
    }
    .btn-row {
        height: 3;
        margin-top: 0;
        align: center middle;
    }
    .btn-row Button {
        margin: 0 1;
    }
    .browse-btn {
        width: 14;
        min-width: 14;
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Pacote CFW:", classes="field-label")
        with Horizontal(classes="input-row"):
            yield Input(placeholder="/caminho/para/pacote-cfw", id="pkg-path", classes="field-input")
            yield Button("Procurar", id="browse-pkg", classes="browse-btn")

        yield InfoPanel(title="Resumo", id="install-summary")

        yield ProgressBar(total=100, id="install-progress", show_eta=False)
        yield Label("", id="install-progress-label")

        with Horizontal(classes="btn-row"):
            yield Button("Instalar CFW", id="install-btn", variant="primary")
        yield Label("", id="install-status")

    def on_mount(self) -> None:
        self.border_title = "Instalação de CFW"

    def set_package_path(self, path: str) -> None:
        self.query_one("#pkg-path", Input).value = path

    def get_package_path(self) -> str:
        return self.query_one("#pkg-path", Input).value.strip()

    def update_summary(self, file_count: int, size_mb: float, free_gb: float) -> None:
        from rich.table import Table

        table = Table(show_header=False, show_edge=False, pad_edge=False)
        table.add_column("chave", style="bold #f8f8f2")
        table.add_column("valor", style="#50fa7b")
        table.add_row("Arquivos", str(file_count))
        table.add_row("Tamanho", f"~{size_mb:.0f}MB")
        table.add_row("Espaço livre", f"{free_gb:.1f}GB")

        panel = self.query_one("#install-summary", InfoPanel)
        panel.set_content(table)

    def update_progress(self, current: int, total: int, filename: str) -> None:
        bar = self.query_one("#install-progress", ProgressBar)
        if total > 0:
            bar.update(progress=current * 100 // total)
        label = self.query_one("#install-progress-label", Label)
        label.update(filename)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "browse-pkg":
            from fusectl.ui.screens.file_picker import DirectoryPicker

            start = str(Path.cwd())

            def on_selected(path) -> None:
                if path is not None:
                    self.query_one("#pkg-path", Input).value = str(path)

            self.app.push_screen(DirectoryPicker(start_path=start), on_selected)

    def set_status(self, message: str, success: bool = True) -> None:
        label = self.query_one("#install-status", Label)
        label.update(message)
        label.set_classes("status-ok" if success else "status-err")
        bar = self.query_one("#install-progress", ProgressBar)
        if success:
            bar.update(progress=100)
        else:
            bar.update(progress=0)

    def set_busy(self, busy: bool) -> None:
        self.query_one("#install-btn", Button).disabled = busy
