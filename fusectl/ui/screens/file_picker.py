from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, Static


class DirectoryPicker(ModalScreen[Path | None]):

    DEFAULT_CSS = """
    DirectoryPicker {
        align: center middle;
    }

    #picker-dialog {
        width: 90;
        height: 30;
        background: #282a36;
        border: round #6272a4;
        padding: 1 2;
    }

    #picker-title {
        text-align: center;
        color: #8be9fd;
        text-style: bold;
        margin-bottom: 1;
    }

    #picker-tree {
        height: 1fr;
        background: #44475a;
        border: round #6272a4;
        margin-bottom: 1;
    }

    #picker-selected {
        height: 1;
        color: #8be9fd;
        margin-bottom: 1;
    }

    #picker-buttons {
        align: center middle;
        height: 3;
    }

    #picker-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: str = "/") -> None:
        super().__init__()
        self._start = start_path
        self._selected: Path | None = None

    def compose(self) -> ComposeResult:
        with Static(id="picker-dialog"):
            yield Label("Selecionar diretório", id="picker-title")
            yield DirectoryTree(self._start, id="picker-tree")
            yield Label("", id="picker-selected")
            with Horizontal(id="picker-buttons"):
                yield Button("Selecionar", id="picker-ok", variant="primary")
                yield Button("Cancelar", id="picker-cancel")

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self._selected = event.path
        self.query_one("#picker-selected", Label).update(f"  {event.path}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "picker-ok":
            self.dismiss(self._selected)
        else:
            self.dismiss(None)
