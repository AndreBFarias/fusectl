from pathlib import Path

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from textual.app import ComposeResult
from textual.widgets import Button, Label, Static


_BANNER_ART_FALLBACK = r"""
   ___                     _   _
  / _|_   _ ___  ___  ___| |_| |
 | |_| | | / __|/ _ \/ __| __| |
 |  _| |_| \__ \  __/ (__| |_| |
 |_|  \__,_|___/\___|\___|\__|_|
"""


def _load_banner_art() -> str:
    logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_ascii.txt"
    try:
        return logo_path.read_text(encoding="utf-8")
    except OSError:
        return _BANNER_ART_FALLBACK


_BANNER_ART = _load_banner_art()


class Banner(Static):

    DEFAULT_CSS = """
    Banner {
        height: auto;
        margin-bottom: 0;
        content-align: center top;
    }
    """

    def render(self) -> Text:
        text = Text()
        text.append(_BANNER_ART.rstrip(), style="bold #bd93f9")
        text.append("\n  Gerenciador Linux para CFW Nintendo Switch", style="#8be9fd")
        return text


class StatusIndicator(Static):

    DEFAULT_CSS = """
    StatusIndicator {
        height: 1;
    }
    """

    _STYLES = {
        "ok": ("*", "bold #50fa7b"),
        "warn": ("*", "bold #f1fa8c"),
        "err": ("*", "bold #ff5555"),
        "none": ("-", "#6272a4"),
    }

    def __init__(self, label: str = "", state: str = "none", detail: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._state = state
        self._detail = detail

    def set_state(self, state: str, detail: str = "") -> None:
        self._state = state
        self._detail = detail
        self.refresh()

    def render(self) -> Text:
        symbol, style = self._STYLES.get(self._state, self._STYLES["none"])
        text = Text()
        text.append(f"  {symbol} ", style=style)
        text.append(f"{self._label}", style="bold #f8f8f2")
        if self._detail:
            text.append(f"  {self._detail}", style="#6272a4")
        return text


class NavBar(Static):

    DEFAULT_CSS = """
    NavBar {
        height: 1;
        background: #bd93f9;
        padding: 0 1;
        layout: horizontal;
    }
    #nav-title {
        color: #282a36;
        text-style: bold;
        width: auto;
    }
    #nav-breadcrumb {
        color: #282a36;
        width: auto;
    }
    #nav-status {
        color: #282a36;
        width: 1fr;
        text-align: right;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._breadcrumb = "Home"
        self._status_text = "RCM: --  |  SD: --"

    def compose(self) -> ComposeResult:
        yield Label("fusectl ", id="nav-title")
        yield Label(f"> {self._breadcrumb}", id="nav-breadcrumb")
        yield Label(self._status_text, id="nav-status")

    def update_breadcrumb(self, name: str) -> None:
        self._breadcrumb = name
        try:
            self.query_one("#nav-breadcrumb", Label).update(f"> {name}")
        except Exception:
            pass

    def update_status(self, text: str) -> None:
        self._status_text = text
        try:
            self.query_one("#nav-status", Label).update(text)
        except Exception:
            pass


class Toolbar(Static):

    DEFAULT_CSS = """
    Toolbar {
        height: 3;
        background: #bd93f9;
        layout: horizontal;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Fusectl", id="tb-context")
        yield Button("Atualizar", id="tb-refresh")
        yield Button("Limpar", id="tb-clear")
        yield Button("Fechar", id="tb-quit")

    def set_context_label(self, label: str) -> None:
        self.query_one("#tb-context", Button).label = label


class InfoPanel(Static):

    DEFAULT_CSS = """
    InfoPanel {
        height: auto;
        margin: 0 0;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._content: RenderableType | None = None

    def set_content(self, content: RenderableType) -> None:
        self._content = content
        self.refresh()

    def render(self) -> Panel:
        content = self._content if self._content else Text("Carregando...", style="#6272a4")
        return Panel(
            content,
            title=self._title,
            title_align="left",
            border_style="#bd93f9",
            padding=(0, 1),
        )
