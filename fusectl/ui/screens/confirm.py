from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmScreen(ModalScreen[bool]):

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 60;
        height: auto;
        background: #282a36;
        border: round #6272a4;
        padding: 2 4;
    }

    #confirm-message {
        margin-bottom: 2;
        text-align: center;
        color: #f8f8f2;
    }

    #confirm-buttons {
        align: center middle;
        height: 3;
    }

    #confirm-yes {
        margin-right: 2;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Static(id="confirm-dialog"):
            yield Label(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Confirmar", id="confirm-yes", variant="primary")
                yield Button("Cancelar", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")
