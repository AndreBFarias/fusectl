from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Input, Label, ProgressBar

from fusectl.ui.widgets import InfoPanel


class UpdateScreen(Vertical):

    DEFAULT_CSS = """
    #version-diff-panel {
        margin: 0 0;
    }
    #update-progress {
        margin: 0 0;
    }
    #update-progress-label {
        margin: 0 0;
        height: 1;
    }
    #update-status {
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
        yield InfoPanel(title="Versões", id="version-diff-panel")

        yield Label("Pacote CFW:", classes="field-label")
        with Horizontal(classes="input-row"):
            yield Input(placeholder="/caminho/para/pacote-cfw", id="upd-pkg-path", classes="field-input")
            yield Button("Procurar", id="browse-upd-pkg", classes="browse-btn")

        yield Checkbox("Forçar atualização (mesma versão)", id="force-check")

        yield ProgressBar(total=100, id="update-progress", show_eta=False)
        yield Label("", id="update-progress-label")

        with Horizontal(classes="btn-row"):
            yield Button("Atualizar CFW", id="update-btn", variant="warning")
        yield Label("", id="update-status")

    def on_mount(self) -> None:
        self.border_title = "Atualização de CFW"

    def set_package_path(self, path: str) -> None:
        self.query_one("#upd-pkg-path", Input).value = path

    def get_package_path(self) -> str:
        return self.query_one("#upd-pkg-path", Input).value.strip()

    def is_force(self) -> bool:
        return self.query_one("#force-check", Checkbox).value

    def show_version_diff(self, pkg_ver: str | None, sd_ver: str | None) -> None:
        from rich.text import Text

        pkg = pkg_ver or "?"
        sd = sd_ver or "?"

        text = Text()
        text.append("  Instalada: ", style="bold #f8f8f2")
        text.append(sd, style="bold #ff5555" if sd == "?" else "bold #f1fa8c")
        text.append("  ->  ", style="bold #ffb86c")
        text.append("Pacote: ", style="bold #f8f8f2")
        text.append(pkg, style="bold #50fa7b" if pkg != "?" else "bold #f1fa8c")

        panel = self.query_one("#version-diff-panel", InfoPanel)
        panel.set_content(text)

    def update_progress(self, current: int, total: int, filename: str) -> None:
        bar = self.query_one("#update-progress", ProgressBar)
        if total > 0:
            bar.update(progress=current * 100 // total)
        label = self.query_one("#update-progress-label", Label)
        label.update(filename)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "browse-upd-pkg":
            from fusectl.ui.screens.file_picker import DirectoryPicker

            start = str(Path.cwd())

            def on_selected(path) -> None:
                if path is not None:
                    self.query_one("#upd-pkg-path", Input).value = str(path)

            self.app.push_screen(DirectoryPicker(start_path=start), on_selected)

    def set_status(self, message: str, success: bool = True) -> None:
        label = self.query_one("#update-status", Label)
        label.update(message)
        label.set_classes("status-ok" if success else "status-err")
        bar = self.query_one("#update-progress", ProgressBar)
        if success:
            bar.update(progress=100)
        else:
            bar.update(progress=0)

    def set_busy(self, busy: bool) -> None:
        self.query_one("#update-btn", Button).disabled = busy
