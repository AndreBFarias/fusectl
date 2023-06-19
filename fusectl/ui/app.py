from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Button, Checkbox, ContentSwitcher, Input, Label, ProgressBar

from rich.text import Text
from textual import work

from fusectl.core.config import find_package_dir, is_cfw_package, list_payloads
from fusectl.core.logger import get_logger, setup_logging
from fusectl.core.version import read_installed_version, read_package_version
from fusectl.ui.screens.confirm import ConfirmScreen
from fusectl.ui.screens.firmware import FirmwareScreen
from fusectl.ui.screens.home import HomeScreen
from fusectl.ui.screens.install import InstallScreen
from fusectl.ui.screens.rcm import RCMScreen
from fusectl.ui.screens.update import UpdateScreen
from fusectl.ui.widgets import InfoPanel, Toolbar

log = get_logger("ui.app")

DRACULA_CSS = """
$background: #282a36;
$surface: #44475a;
$foreground: #f8f8f2;
$comment: #6272a4;
$cyan: #8be9fd;
$green: #50fa7b;
$orange: #ffb86c;
$pink: #ff79c6;
$purple: #bd93f9;
$red: #ff5555;
$yellow: #f1fa8c;

Screen {
    background: $background;
    color: $foreground;
}

ContentSwitcher {
    background: $background;
}

VerticalScroll {
    background: $background;
    padding: 0 1;
}

RCMScreen, InstallScreen, UpdateScreen, FirmwareScreen {
    border: round $purple;
    padding: 0 1;
    margin: 0 0 0 0;
    height: auto;
}

HomeScreen {
    padding: 0 1;
    align: center top;
    height: auto;
}

Button {
    background: $comment;
    color: $foreground;
    border: none;
    padding: 0 3;
    margin: 0 0;
    min-width: 16;
}

Toolbar Button {
    width: 1fr;
    border: round $purple;
    margin: 0 1;
    min-width: 0;
    background: $purple;
    color: $background;
    text-style: bold;
}

Toolbar Button:hover {
    background: $background;
    color: $purple;
    border: round $purple;
}

#home-buttons Button {
    border: round $purple;
    margin: 0 2;
}

#home-start { background: $cyan; color: $background; text-style: bold; }
#home-refresh { background: $comment; color: $foreground; }
#home-quit { background: $red; color: $foreground; }

Button:hover {
    background: $cyan;
    color: $background;
}

Button.-primary {
    background: $cyan;
    color: $background;
    text-style: bold;
}

Button.-primary:hover {
    background: $green;
}

Button.-warning {
    background: $orange;
    color: $background;
    text-style: bold;
}

Button.-warning:hover {
    background: $yellow;
    color: $background;
}

Button:disabled {
    background: $surface;
    color: $comment;
    opacity: 60%;
}

Input {
    background: $surface;
    color: $foreground;
    border: round $comment;
    padding: 0 1;
}

Input:focus {
    border: round $cyan;
}

Input > .input--placeholder {
    color: $comment;
}

OptionList {
    background: $surface;
    color: $foreground;
    border: round $comment;
    scrollbar-background: $surface;
    scrollbar-color: $comment;
    scrollbar-color-hover: $cyan;
}

OptionList > .option-list--option-highlighted {
    background: $cyan;
    color: $background;
    text-style: bold;
}

OptionList > .option-list--option-hover {
    background: $comment;
}

ProgressBar Bar {
    background: $surface;
    color: $cyan;
}

ProgressBar Bar > .bar--bar {
    color: $cyan;
}

ProgressBar Bar > .bar--complete {
    color: $green;
}

ProgressBar PercentageStatus {
    color: $foreground;
    text-style: bold;
}

Checkbox {
    background: $background;
    color: $foreground;
    margin: 0 0;
}

Checkbox > .toggle--button {
    background: $surface;
    color: $comment;
}

Checkbox.-on > .toggle--button {
    color: $green;
}

Label {
    color: $foreground;
    margin: 0 0;
}

.status-ok {
    color: $green;
}

.status-warn {
    color: $yellow;
}

.status-err {
    color: $red;
}

.field-label {
    color: $foreground;
    margin-top: 0;
    text-style: bold;
}

.field-input {
    margin-bottom: 0;
    width: 1fr;
}

#payload-list {
    height: 8;
    margin-bottom: 0;
}

#inject-result {
    margin-top: 0;
}

#status-row {
    height: auto;
    align: center middle;
}

#home-status-panel {
    width: 60;
}

#install-progress, #update-progress, #firmware-progress {
    margin-top: 0;
}

#install-status, #update-status, #firmware-status {
    margin-top: 0;
}

.input-row {
    height: auto;
}

.rcm-buttons Button, .btn-row Button {
    border: round $purple;
    margin: 0 1;
}

.browse-btn {
    width: auto;
    min-width: 12;
    margin-left: 1;
    padding: 0 1;
}
"""


class FuseCtlApp(App):
    CSS = DRACULA_CSS
    TITLE = "fusectl"
    SUB_TITLE = "Nintendo Switch CFW Manager"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Sair", show=False),
        Binding("f5", "refresh", "Atualizar", show=False),
        Binding("delete", "clear_all", "Limpar", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._pkg_dir: Path | None = None
        self._sd_paths: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Toolbar(id="toolbar")
        with ContentSwitcher(id="content", initial="view-home"):
            with VerticalScroll(id="view-home"):
                yield HomeScreen()
            with VerticalScroll(id="view-ops"):
                yield RCMScreen()
                yield InstallScreen()
                yield UpdateScreen()
                yield FirmwareScreen()

    def on_mount(self) -> None:
        setup_logging()
        self._poll_status()
        self.set_interval(1.5, self._poll_status)

    def _switch_to_home(self) -> None:
        self.query_one("#content", ContentSwitcher).current = "view-home"
        self.query_one("#toolbar", Toolbar).set_context_label("Fusectl")

    def _switch_to_ops(self) -> None:
        self.query_one("#content", ContentSwitcher).current = "view-ops"
        self.query_one("#toolbar", Toolbar).set_context_label("Home")

    def _update_global_status(self, rcm_connected: bool) -> None:
        pass

    def _poll_status(self) -> None:
        self._detect_package()
        rcm_connected = self._check_rcm()
        self._detect_sd()

        self._update_global_status(rcm_connected)

        pkg_version = None
        if self._pkg_dir:
            pkg_version = read_package_version(self._pkg_dir)

        sd_version = None
        if self._sd_paths:
            sd_version = read_installed_version(self._sd_paths[0])

        free_gb: float | None = None
        if self._sd_paths:
            try:
                from fusectl.sdcard.detector import get_sd_free_space
                free_bytes = get_sd_free_space(self._sd_paths[0])
                free_gb = free_bytes / (1024 ** 3)
            except Exception as exc:
                log.debug("Espaço livre: %s", exc)

        home = self.query_one(HomeScreen)
        home.refresh_status(pkg_version, sd_version, rcm_connected, self._sd_paths, free_gb)

        rcm_screen = self.query_one(RCMScreen)
        rcm_screen.update_rcm_status(rcm_connected)

        if self._pkg_dir:
            payloads = list_payloads(self._pkg_dir)
            rcm_screen.update_payloads(payloads)

            install_screen = self.query_one(InstallScreen)
            if not install_screen.get_package_path():
                install_screen.set_package_path(str(self._pkg_dir))

            update_screen = self.query_one(UpdateScreen)
            if not update_screen.get_package_path():
                update_screen.set_package_path(str(self._pkg_dir))
            update_screen.show_version_diff(pkg_version, sd_version)

        firmware_screen = self.query_one(FirmwareScreen)
        if not firmware_screen.get_firmware_path():
            from fusectl.firmware.manager import find_firmware_dir
            fw_source = find_firmware_dir(package_dir=self._pkg_dir)
            if fw_source:
                firmware_screen.set_firmware_path(str(fw_source))

    def _detect_package(self) -> None:
        if self._pkg_dir and is_cfw_package(self._pkg_dir):
            return
        self._pkg_dir = find_package_dir()

    def _check_rcm(self) -> bool:
        try:
            from fusectl.rcm.detector import is_rcm_available
            return is_rcm_available()
        except Exception as exc:
            log.debug("Detecção RCM: %s", exc)
            return False

    def _detect_sd(self) -> None:
        try:
            from fusectl.sdcard.detector import find_switch_sd
            self._sd_paths = find_switch_sd()
        except Exception as exc:
            log.debug("Detecção SD: %s", exc)
            self._sd_paths = []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "tb-context":
            cs = self.query_one("#content", ContentSwitcher)
            if cs.current == "view-home":
                self._switch_to_ops()
            else:
                self._switch_to_home()
        elif bid == "tb-refresh":
            self._poll_status()
        elif bid == "tb-clear":
            self.action_clear_all()
        elif bid == "tb-quit":
            self.exit()
        elif bid == "home-start":
            self._switch_to_ops()
        elif bid == "home-refresh":
            self._poll_status()
        elif bid == "home-quit":
            self.exit()
        elif bid == "inject-btn":
            self._do_inject()
        elif bid == "install-btn":
            self._do_install()
        elif bid == "update-btn":
            self._do_update()
        elif bid == "firmware-btn":
            self._do_firmware()

    def action_refresh(self) -> None:
        self._poll_status()

    def action_clear_all(self) -> None:
        self._clear_install()
        self._clear_update()
        self._clear_firmware()

    def _clear_install(self) -> None:
        screen = self.query_one(InstallScreen)
        screen.query_one("#pkg-path", Input).value = ""
        screen.query_one("#install-status", Label).update("")
        screen.query_one("#install-progress-label", Label).update("")
        screen.query_one(ProgressBar).update(progress=0)
        screen.query_one("#install-summary", InfoPanel).set_content(
            Text("Carregando...", style="#6272a4")
        )

    def _clear_update(self) -> None:
        screen = self.query_one(UpdateScreen)
        screen.query_one("#upd-pkg-path", Input).value = ""
        screen.query_one("#update-status", Label).update("")
        screen.query_one("#update-progress-label", Label).update("")
        screen.query_one(ProgressBar).update(progress=0)
        screen.query_one("#version-diff-panel", InfoPanel).set_content(
            Text("Carregando...", style="#6272a4")
        )
        screen.query_one("#force-check", Checkbox).value = False

    def _clear_firmware(self) -> None:
        screen = self.query_one(FirmwareScreen)
        screen.query_one("#fw-source", Input).value = ""
        screen.query_one("#firmware-status", Label).update("")
        screen.query_one("#firmware-progress-label", Label).update("")
        screen.query_one(ProgressBar).update(progress=0)
        screen.query_one("#firmware-summary", InfoPanel).set_content(
            Text("Carregando...", style="#6272a4")
        )

    def _do_inject(self) -> None:
        rcm_screen = self.query_one(RCMScreen)
        if not rcm_screen._rcm_connected:
            rcm_screen.set_result("Nenhum Switch conectado", success=False)
            self.notify("Conecte o Switch em modo RCM", severity="warning")
            return
        payload = rcm_screen.get_selected_payload()
        if not payload:
            rcm_screen.set_result("Selecione um payload", success=False)
            self.notify("Selecione um payload antes de injetar", severity="warning")
            return

        rcm_screen.query_one("#inject-btn", Button).disabled = True
        rcm_screen.set_result(f"Injetando {payload.name}...")
        self._run_inject(payload)

    @work(thread=True)
    def _run_inject(self, payload: Path) -> None:
        rcm_screen = self.query_one(RCMScreen)
        try:
            from fusectl.rcm.injector import inject
            inject(payload)
            self.call_from_thread(
                rcm_screen.set_result, f"Payload injetado: {payload.name}"
            )
            self.call_from_thread(
                self.notify, f"Payload injetado: {payload.name}", severity="information"
            )
        except Exception as exc:
            self.call_from_thread(
                rcm_screen.set_result, f"Erro: {exc}", False
            )
            self.call_from_thread(
                self.notify, f"Erro na injeção: {exc}", severity="error"
            )
        finally:
            btn = rcm_screen.query_one("#inject-btn", Button)
            if rcm_screen._rcm_connected:
                self.call_from_thread(setattr, btn, "disabled", False)

    def _do_install(self) -> None:
        screen = self.query_one(InstallScreen)
        pkg_path = screen.get_package_path()

        if not pkg_path:
            screen.set_status("Pacote CFW não detectado", success=False)
            return
        if not self._sd_paths:
            screen.set_status("SD não detectado", success=False)
            self.notify("Insira o cartão SD", severity="warning")
            return

        pkg_dir = Path(pkg_path)
        sd_root = self._sd_paths[0]

        from fusectl.sdcard.installer import _collect_files
        from fusectl.sdcard.detector import get_sd_free_space

        file_count = len(_collect_files(pkg_dir))
        size_bytes = sum(
            f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file()
        )
        free_bytes = get_sd_free_space(sd_root)
        screen.update_summary(file_count, size_bytes / (1024 * 1024), free_bytes / (1024**3))

        if size_bytes > free_bytes:
            screen.set_status("Espaço insuficiente no SD", success=False)
            self.notify("Espaço insuficiente no SD", severity="error")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                screen.set_busy(True)
                self._run_install(pkg_dir, sd_root)

        self.push_screen(
            ConfirmScreen(f"Instalar CFW em {sd_root}?\n{file_count} arquivos, ~{size_bytes / (1024 * 1024):.0f}MB"),
            on_confirm,
        )

    @work(thread=True)
    def _run_install(self, pkg_dir: Path, sd_root: Path) -> None:
        from fusectl.sdcard.installer import install

        screen = self.query_one(InstallScreen)
        try:
            errors = install(
                pkg_dir,
                sd_root,
                progress_callback=lambda c, t, f: self.call_from_thread(
                    screen.update_progress, c, t, f
                ),
            )
            if errors:
                self.call_from_thread(
                    screen.set_status, f"{len(errors)} erro(s) durante instalação", False
                )
                self.call_from_thread(
                    self.notify, f"{len(errors)} erro(s) durante instalação", severity="error"
                )
            else:
                self.call_from_thread(screen.set_status, "Instalação concluída")
                self.call_from_thread(
                    self.notify, "Instalação concluída com sucesso", severity="information"
                )
        except Exception as exc:
            self.call_from_thread(screen.set_status, f"Erro: {exc}", False)
            self.call_from_thread(self.notify, f"Erro: {exc}", severity="error")
        finally:
            self.call_from_thread(screen.set_busy, False)

    def _do_update(self) -> None:
        screen = self.query_one(UpdateScreen)
        pkg_path = screen.get_package_path()

        if not pkg_path:
            screen.set_status("Pacote CFW não detectado", success=False)
            return
        if not self._sd_paths:
            screen.set_status("SD não detectado", success=False)
            self.notify("Insira o cartão SD", severity="warning")
            return

        sd_root = self._sd_paths[0]

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                screen.set_busy(True)
                self._run_update(Path(pkg_path), sd_root, screen.is_force())

        self.push_screen(
            ConfirmScreen(f"Atualizar CFW em {sd_root}?"),
            on_confirm,
        )

    @work(thread=True)
    def _run_update(self, pkg_dir: Path, sd_root: Path, force: bool) -> None:
        from fusectl.sdcard.updater import update

        screen = self.query_one(UpdateScreen)
        try:
            errors = update(
                pkg_dir,
                sd_root,
                force=force,
                progress_callback=lambda c, t, f: self.call_from_thread(
                    screen.update_progress, c, t, f
                ),
            )
            if errors:
                self.call_from_thread(
                    screen.set_status, f"{len(errors)} erro(s) durante atualização", False
                )
                self.call_from_thread(
                    self.notify, f"{len(errors)} erro(s) durante atualização", severity="error"
                )
            else:
                self.call_from_thread(screen.set_status, "Atualização concluída")
                self.call_from_thread(
                    self.notify, "Atualização concluída com sucesso", severity="information"
                )
        except Exception as exc:
            self.call_from_thread(screen.set_status, f"Erro: {exc}", False)
            self.call_from_thread(self.notify, f"Erro: {exc}", severity="error")
        finally:
            self.call_from_thread(screen.set_busy, False)

    def _do_firmware(self) -> None:
        screen = self.query_one(FirmwareScreen)
        fw_path = screen.get_firmware_path()

        if not fw_path:
            screen.set_status("Firmware não detectado", success=False)
            return
        if not self._sd_paths:
            screen.set_status("SD não detectado", success=False)
            self.notify("Insira o cartão SD", severity="warning")
            return

        fw_dir = Path(fw_path)
        sd_root = self._sd_paths[0]

        from fusectl.firmware.manager import _collect_nca_files
        from fusectl.sdcard.detector import get_sd_free_space

        nca_files = _collect_nca_files(fw_dir)
        if not nca_files:
            screen.set_status("Nenhum arquivo NCA encontrado", success=False)
            self.notify("Nenhum arquivo NCA encontrado", severity="error")
            return

        size_bytes = sum(f.stat().st_size for f in nca_files)
        free_bytes = get_sd_free_space(sd_root)
        screen.update_summary(len(nca_files), size_bytes / (1024 * 1024), free_bytes / (1024**3))

        if size_bytes > free_bytes:
            screen.set_status("Espaço insuficiente no SD", success=False)
            self.notify("Espaço insuficiente no SD", severity="error")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                screen.set_busy(True)
                self._run_firmware(fw_dir, sd_root)

        self.push_screen(
            ConfirmScreen(
                f"Copiar firmware para {sd_root}?\n{len(nca_files)} NCAs, ~{size_bytes / (1024 * 1024):.0f}MB"
            ),
            on_confirm,
        )

    @work(thread=True)
    def _run_firmware(self, fw_dir: Path, sd_root: Path) -> None:
        from fusectl.firmware.manager import install_firmware

        screen = self.query_one(FirmwareScreen)
        try:
            errors = install_firmware(
                fw_dir,
                sd_root,
                progress_callback=lambda c, t, f: self.call_from_thread(
                    screen.update_progress, c, t, f
                ),
            )
            if errors:
                self.call_from_thread(
                    screen.set_status, f"{len(errors)} erro(s) durante copia", False
                )
                self.call_from_thread(
                    self.notify, f"{len(errors)} erro(s) durante copia de firmware", severity="error"
                )
            else:
                self.call_from_thread(screen.set_status, "Firmware copiado")
                self.call_from_thread(
                    self.notify, "Firmware copiado com sucesso", severity="information"
                )
        except Exception as exc:
            self.call_from_thread(screen.set_status, f"Erro: {exc}", False)
            self.call_from_thread(self.notify, f"Erro: {exc}", severity="error")
        finally:
            self.call_from_thread(screen.set_busy, False)

    def action_quit_app(self) -> None:
        self.exit()
