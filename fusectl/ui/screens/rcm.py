from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, OptionList
from textual.widgets.option_list import Option

from fusectl.ui.widgets import InfoPanel


class RCMScreen(Vertical):

    DEFAULT_CSS = """
    #rcm-conn-panel {
        margin-bottom: 0;
    }
    #payload-list {
        height: 8;
        margin: 0 0 0 0;
    }
    .rcm-buttons {
        height: 3;
        margin-top: 0;
        align: center middle;
    }
    .rcm-buttons Button {
        margin: 0 1;
    }
    #inject-result {
        margin-top: 0;
        height: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._payloads: list[Path] = []
        self._rcm_connected = False

    def compose(self) -> ComposeResult:
        yield InfoPanel(title="Conexão USB", id="rcm-conn-panel")
        yield Label("Payloads disponíveis:", classes="field-label")
        yield OptionList(id="payload-list")
        with Horizontal(classes="rcm-buttons"):
            yield Button("Injetar Payload", id="inject-btn", variant="primary", disabled=True)
        yield Label("", id="inject-result")

    def on_mount(self) -> None:
        self.border_title = "RCM - Injeção de Payload"

    def update_rcm_status(self, connected: bool) -> None:
        from rich.text import Text

        self._rcm_connected = connected
        btn = self.query_one("#inject-btn", Button)

        panel = self.query_one("#rcm-conn-panel", InfoPanel)
        if connected:
            text = Text()
            text.append("Status: ", style="bold #f8f8f2")
            text.append("* Switch detectado em modo RCM", style="bold #50fa7b")
            panel.set_content(text)
            if self._payloads:
                btn.disabled = False
        else:
            text = Text()
            text.append("Status: ", style="bold #f8f8f2")
            text.append("* Nenhum Switch detectado", style="#ff5555")
            panel.set_content(text)
            btn.disabled = True

    def update_payloads(self, payloads: list[Path]) -> None:
        if payloads == self._payloads:
            return
        option_list = self.query_one("#payload-list", OptionList)
        prev_idx = option_list.highlighted
        prev_name = (
            self._payloads[prev_idx].name
            if prev_idx is not None and 0 <= prev_idx < len(self._payloads)
            else None
        )

        self._payloads = payloads
        option_list.clear_options()
        restore_idx = None
        for i, p in enumerate(payloads):
            option_list.add_option(Option(f"{p.name}", id=str(p)))
            if p.name == prev_name:
                restore_idx = i

        if restore_idx is not None:
            option_list.highlighted = restore_idx

    def get_selected_payload(self) -> Path | None:
        option_list = self.query_one("#payload-list", OptionList)
        idx = option_list.highlighted
        if idx is not None and 0 <= idx < len(self._payloads):
            return self._payloads[idx]
        return None

    def set_result(self, message: str, success: bool = True) -> None:
        label = self.query_one("#inject-result", Label)
        label.update(message)
        label.set_classes("status-ok" if success else "status-err")
