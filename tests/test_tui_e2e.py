"""Testes fim-a-fim da TUI fusectl usando Textual pilot (headless)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import Button, ContentSwitcher, Input, Label, OptionList

from fusectl.ui.app import FuseCtlApp
from fusectl.ui.widgets import Toolbar
from fusectl.ui.screens.firmware import FirmwareScreen
from fusectl.ui.screens.home import HomeScreen
from fusectl.ui.screens.install import InstallScreen
from fusectl.ui.screens.rcm import RCMScreen
from fusectl.ui.screens.update import UpdateScreen
from fusectl.ui.widgets import InfoPanel


class TestNavegacao:

    @pytest.mark.asyncio
    async def test_views_presentes(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            assert app.query_one("#content", ContentSwitcher) is not None
            assert app.query_one("#view-home") is not None
            assert app.query_one("#view-ops") is not None

    @pytest.mark.asyncio
    async def test_home_visivel_inicialmente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            cs = app.query_one("#content", ContentSwitcher)
            assert cs.current == "view-home"

    @pytest.mark.asyncio
    async def test_navegacao_home_ops(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            cs = app.query_one("#content", ContentSwitcher)

            app._switch_to_ops()
            assert cs.current == "view-ops"

            app._switch_to_home()
            assert cs.current == "view-home"



class TestToolbar:

    @pytest.mark.asyncio
    async def test_toolbar_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            toolbar = app.query_one("#toolbar", Toolbar)
            assert toolbar is not None

    @pytest.mark.asyncio
    async def test_toolbar_label_contextual_muda(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            toolbar = app.query_one("#toolbar", Toolbar)
            ctx_btn = toolbar.query_one("#tb-context", Button)
            assert str(ctx_btn.label) == "Fusectl"

            app._switch_to_ops()
            assert str(ctx_btn.label) == "Home"

            app._switch_to_home()
            assert str(ctx_btn.label) == "Fusectl"

    @pytest.mark.asyncio
    async def test_toolbar_botao_context_navega(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            cs = app.query_one("#content", ContentSwitcher)
            toolbar = app.query_one("#toolbar", Toolbar)
            ctx_btn = toolbar.query_one("#tb-context", Button)

            event = Button.Pressed(ctx_btn)
            app.on_button_pressed(event)
            assert cs.current == "view-ops"

            event = Button.Pressed(ctx_btn)
            app.on_button_pressed(event)
            assert cs.current == "view-home"


class TestAtalhos:

    @pytest.mark.asyncio
    async def test_f5_dispara_refresh(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            with patch.object(app, "_poll_status") as mock_poll:
                await pilot.press("f5")
                mock_poll.assert_called()

    @pytest.mark.asyncio
    async def test_del_limpa_campos(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path("/tmp/pkg")

            await pilot.press("delete")

            assert screen.get_package_path() == ""


class TestHomeScreen:

    @pytest.mark.asyncio
    async def test_home_mostra_banner(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            svg = app.export_screenshot()
            assert "fusectl" in svg.lower()

    @pytest.mark.asyncio
    async def test_home_mostra_status_panel(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            home = app.query_one(HomeScreen)
            panel = home.query_one("#home-status-panel", InfoPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_toolbar_refresh_dispara_poll(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            with patch.object(app, "_poll_status") as mock_poll:
                toolbar = app.query_one("#toolbar", Toolbar)
                btn = toolbar.query_one("#tb-refresh", Button)
                event = Button.Pressed(btn)
                app.on_button_pressed(event)
                mock_poll.assert_called_once()

    @pytest.mark.asyncio
    async def test_home_espaço_livre_sd(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            home = app.query_one(HomeScreen)
            home.refresh_status("21.2.0-0", "20.1.0-0", True, [Path("/mnt/sd")], free_gb=14.5)
            panel = home.query_one("#home-status-panel", InfoPanel)
            assert panel._content is not None

    @pytest.mark.asyncio
    async def test_home_botao_iniciar_navega(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            cs = app.query_one("#content", ContentSwitcher)
            home = app.query_one(HomeScreen)
            btn = home.query_one("#home-start", Button)
            event = Button.Pressed(btn)
            app.on_button_pressed(event)
            assert cs.current == "view-ops"

    @pytest.mark.asyncio
    async def test_home_botao_atualizar(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            with patch.object(app, "_poll_status") as mock_poll:
                home = app.query_one(HomeScreen)
                btn = home.query_one("#home-refresh", Button)
                event = Button.Pressed(btn)
                app.on_button_pressed(event)
                mock_poll.assert_called_once()


class TestRCMScreen:

    @pytest.mark.asyncio
    async def test_rcm_botao_inject_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            assert rcm.query_one("#inject-btn", Button) is not None

    @pytest.mark.asyncio
    async def test_rcm_inject_desabilitado_sem_conexão(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_rcm_status(False)
            assert rcm.query_one("#inject-btn", Button).disabled is True

    @pytest.mark.asyncio
    async def test_rcm_inject_habilitado_com_conexão_e_payloads(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/fusee.bin")])
            rcm.update_rcm_status(True)
            assert rcm.query_one("#inject-btn", Button).disabled is False

    @pytest.mark.asyncio
    async def test_selecao_payload_sobrevive_polling(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            payloads = [Path("/tmp/a.bin"), Path("/tmp/b.bin"), Path("/tmp/c.bin")]
            rcm.update_payloads(payloads)

            ol = rcm.query_one("#payload-list", OptionList)
            ol.highlighted = 2
            assert rcm.get_selected_payload() == Path("/tmp/c.bin")

            rcm.update_payloads(payloads)
            assert ol.highlighted == 2
            assert rcm.get_selected_payload() == Path("/tmp/c.bin")

    @pytest.mark.asyncio
    async def test_selecao_restaura_por_nome_apos_reordenacao(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/a.bin"), Path("/tmp/b.bin"), Path("/tmp/c.bin")])

            ol = rcm.query_one("#payload-list", OptionList)
            ol.highlighted = 2  # c.bin

            rcm.update_payloads([Path("/tmp/c.bin"), Path("/tmp/a.bin")])
            assert rcm.get_selected_payload() == Path("/tmp/c.bin")

    @pytest.mark.asyncio
    async def test_inject_sem_conexao_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_rcm_status(False)
            app._do_inject()
            result = str(rcm.query_one("#inject-result", Label).content)
            assert "Nenhum Switch" in result

    @pytest.mark.asyncio
    async def test_inject_sem_selecao_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_rcm_status(True)
            app._do_inject()
            result = str(rcm.query_one("#inject-result", Label).content)
            assert "Selecione" in result

    @pytest.mark.asyncio
    async def test_inject_com_payload_dispara_worker(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/fusee.bin")])
            rcm.update_rcm_status(True)
            rcm.query_one("#payload-list", OptionList).highlighted = 0

            with patch("fusectl.ui.app.FuseCtlApp._run_inject") as mock_run:
                app._do_inject()
                mock_run.assert_called_once_with(Path("/tmp/fusee.bin"))

            assert "Injetando" in str(rcm.query_one("#inject-result", Label).content)
            assert rcm.query_one("#inject-btn", Button).disabled is True

    @pytest.mark.asyncio
    async def test_inject_sucesso_feedback_ui(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/fusee.bin")])
            rcm.update_rcm_status(True)
            rcm.query_one("#payload-list", OptionList).highlighted = 0

            with patch("fusectl.ui.app.FuseCtlApp._run_inject"):
                app._do_inject()

            rcm.set_result("Payload injetado: fusee.bin")
            result = str(rcm.query_one("#inject-result", Label).content)
            assert "injetado" in result.lower()
            assert "fusee.bin" in result

    @pytest.mark.asyncio
    async def test_inject_erro_feedback_ui(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/fusee.bin")])
            rcm.update_rcm_status(True)
            rcm.query_one("#payload-list", OptionList).highlighted = 0

            with patch("fusectl.ui.app.FuseCtlApp._run_inject"):
                app._do_inject()

            rcm.set_result("Erro: USB timeout", success=False)
            result = str(rcm.query_one("#inject-result", Label).content)
            assert "Erro" in result
            assert "USB timeout" in result


class TestInstallScreen:

    @pytest.mark.asyncio
    async def test_install_botao_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            btn = screen.query_one("#install-btn", Button)
            assert "Instalar" in str(btn.label)

    @pytest.mark.asyncio
    async def test_install_inputs_presentes(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            assert screen.query_one("#pkg-path", Input) is not None

    @pytest.mark.asyncio
    async def test_install_sem_pacote_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.query_one("#pkg-path", Input).value = ""
            app._do_install()
            status = str(screen.query_one("#install-status", Label).content)
            assert "não detectado" in status.lower()

    @pytest.mark.asyncio
    async def test_install_sem_sd_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path("/tmp/pkg")
            app._sd_paths = []
            app._do_install()
            status = str(screen.query_one("#install-status", Label).content)
            assert "sd" in status.lower()

    @pytest.mark.asyncio
    async def test_install_executa_e_conclui(self, cnx_package: Path, sd_card: Path) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_install"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_install()
                    mock_push.assert_called_once()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.sdcard.installer import install
            install(cnx_package, sd_card)

            screen.set_status("Instalação concluída")
            screen.set_busy(False)

            status = str(screen.query_one("#install-status", Label).content)
            assert "concluída" in status.lower()
            assert (sd_card / "payload.bin").is_file()

    @pytest.mark.asyncio
    async def test_install_summary_preenchido(self, cnx_package: Path, sd_card: Path) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_install"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen"):
                    app._do_install()

            panel = screen.query_one("#install-summary", InfoPanel)
            assert panel._content is not None


class TestUpdateScreen:

    @pytest.mark.asyncio
    async def test_update_botao_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            btn = screen.query_one("#update-btn", Button)
            assert "Atualizar" in str(btn.label)

    @pytest.mark.asyncio
    async def test_update_sem_pacote_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            screen.query_one("#upd-pkg-path", Input).value = ""
            app._do_update()
            status = str(screen.query_one("#update-status", Label).content)
            assert "não detectado" in status.lower()

    @pytest.mark.asyncio
    async def test_update_sem_sd_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            screen.set_package_path("/tmp/pkg")
            app._sd_paths = []
            app._do_update()
            status = str(screen.query_one("#update-status", Label).content)
            assert "sd" in status.lower()

    @pytest.mark.asyncio
    async def test_update_executa_e_conclui(self, cnx_package: Path, sd_card: Path) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_update"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_update()
                    mock_push.assert_called_once()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.sdcard.updater import update
            update(cnx_package, sd_card)

            screen.set_status("Atualização concluída")
            screen.set_busy(False)

            status = str(screen.query_one("#update-status", Label).content)
            assert "concluída" in status.lower()

    @pytest.mark.asyncio
    async def test_update_version_diff(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            screen.show_version_diff("21.2.0-0", "20.1.0-0")
            panel = screen.query_one("#version-diff-panel", InfoPanel)
            assert panel._content is not None


class TestFirmwareScreen:

    @pytest.mark.asyncio
    async def test_firmware_botao_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            btn = screen.query_one("#firmware-btn", Button)
            assert "Firmware" in str(btn.label)

    @pytest.mark.asyncio
    async def test_firmware_input_presente(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            assert screen.query_one("#fw-source", Input) is not None

    @pytest.mark.asyncio
    async def test_firmware_sem_fonte_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            screen.query_one("#fw-source", Input).value = ""
            app._do_firmware()
            status = str(screen.query_one("#firmware-status", Label).content)
            assert "não detectado" in status.lower()

    @pytest.mark.asyncio
    async def test_firmware_sem_sd_mostra_erro(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            screen.set_firmware_path("/tmp/fw")
            app._sd_paths = []
            app._do_firmware()
            status = str(screen.query_one("#firmware-status", Label).content)
            assert "sd" in status.lower()

    @pytest.mark.asyncio
    async def test_firmware_executa_e_conclui(self, tmp_path: Path) -> None:
        fw_dir = tmp_path / "21.2.0"
        fw_dir.mkdir()
        for i in range(3):
            (fw_dir / f"file{i}.nca").write_bytes(b"\x00" * 64)

        sd_card = tmp_path / "sdcard"
        sd_card.mkdir()

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            screen.set_firmware_path(str(fw_dir))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_firmware"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_firmware()
                    mock_push.assert_called_once()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.firmware.manager import install_firmware
            install_firmware(fw_dir, sd_card)

            screen.set_status("Firmware copiado")
            screen.set_busy(False)

            status = str(screen.query_one("#firmware-status", Label).content)
            assert "copiado" in status.lower()
            assert (sd_card / "firmware").is_dir()

    @pytest.mark.asyncio
    async def test_firmware_summary_preenchido(self, tmp_path: Path) -> None:
        fw_dir = tmp_path / "21.2.0"
        fw_dir.mkdir()
        (fw_dir / "test.nca").write_bytes(b"\x00" * 128)

        sd_card = tmp_path / "sdcard"
        sd_card.mkdir()

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            screen.set_firmware_path(str(fw_dir))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_firmware"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen"):
                    app._do_firmware()

            panel = screen.query_one("#firmware-summary", InfoPanel)
            assert panel._content is not None


class TestFluxoCompletoE2E:

    @pytest.mark.asyncio
    async def test_usuario_navega_e_instala(self, cnx_package: Path, sd_card: Path) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._switch_to_ops()
            cs = app.query_one("#content", ContentSwitcher)
            assert cs.current == "view-ops"

            screen = app.query_one(InstallScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_install"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_install()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.sdcard.installer import install
            install(cnx_package, sd_card)

            screen.set_status("Instalação concluída")
            screen.set_busy(False)

            status = str(screen.query_one("#install-status", Label).content)
            assert "concluída" in status.lower()
            assert (sd_card / "payload.bin").is_file()
            assert (sd_card / "atmosphere").is_dir()
            assert (sd_card / "bootloader" / "hekate_ipl.ini").is_file()

    @pytest.mark.asyncio
    async def test_usuario_atualiza_cfw(self, cnx_package: Path, sd_card: Path) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._switch_to_ops()

            screen = app.query_one(UpdateScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_update"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_update()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.sdcard.updater import update
            update(cnx_package, sd_card)

            screen.set_status("Atualização concluída")
            screen.set_busy(False)

            status = str(screen.query_one("#update-status", Label).content)
            assert "concluída" in status.lower()

    @pytest.mark.asyncio
    async def test_usuario_seleciona_payload_e_injeta(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._switch_to_ops()

            rcm = app.query_one(RCMScreen)
            rcm.update_payloads([Path("/tmp/fusee.bin"), Path("/tmp/tegra.bin")])
            rcm.update_rcm_status(True)
            rcm.query_one("#payload-list", OptionList).highlighted = 1

            with patch("fusectl.ui.app.FuseCtlApp._run_inject") as mock_run:
                app._do_inject()
                mock_run.assert_called_once_with(Path("/tmp/tegra.bin"))

            assert "Injetando tegra.bin" in str(
                rcm.query_one("#inject-result", Label).content
            )

            rcm.set_result("Payload injetado: tegra.bin")
            result = str(rcm.query_one("#inject-result", Label).content)
            assert "injetado" in result.lower()

    @pytest.mark.asyncio
    async def test_usuario_copia_firmware(self, tmp_path: Path) -> None:
        fw_dir = tmp_path / "21.2.0"
        fw_dir.mkdir()
        for i in range(5):
            (fw_dir / f"module{i}.nca").write_bytes(b"\x00" * 32)

        sd_card = tmp_path / "sdcard"
        sd_card.mkdir()

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._switch_to_ops()
            cs = app.query_one("#content", ContentSwitcher)
            assert cs.current == "view-ops"

            screen = app.query_one(FirmwareScreen)
            screen.set_firmware_path(str(fw_dir))
            app._sd_paths = [sd_card]

            with patch("fusectl.ui.app.FuseCtlApp._run_firmware"):
                with patch("fusectl.ui.app.FuseCtlApp.push_screen") as mock_push:
                    app._do_firmware()
                    confirm_callback = mock_push.call_args[0][1]
                    confirm_callback(True)

            from fusectl.firmware.manager import install_firmware
            install_firmware(fw_dir, sd_card)

            screen.set_status("Firmware copiado")
            screen.set_busy(False)

            status = str(screen.query_one("#firmware-status", Label).content)
            assert "copiado" in status.lower()
            assert (sd_card / "firmware").is_dir()
            nca_count = sum(1 for f in (sd_card / "firmware").iterdir() if f.suffix == ".nca")
            assert nca_count == 5


class TestBotoesLimpar:

    @pytest.mark.asyncio
    async def test_limpar_global_reseta_install(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path("/tmp/pkg")
            screen.set_status("Concluído")

            toolbar = app.query_one("#toolbar", Toolbar)
            btn = toolbar.query_one("#tb-clear", Button)
            event = Button.Pressed(btn)
            app.on_button_pressed(event)

            assert screen.get_package_path() == ""
            assert str(screen.query_one("#install-status", Label).content) == ""

    @pytest.mark.asyncio
    async def test_limpar_global_reseta_update(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(UpdateScreen)
            screen.set_package_path("/tmp/pkg")
            screen.set_status("Concluído")

            toolbar = app.query_one("#toolbar", Toolbar)
            btn = toolbar.query_one("#tb-clear", Button)
            event = Button.Pressed(btn)
            app.on_button_pressed(event)

            assert screen.get_package_path() == ""
            assert str(screen.query_one("#update-status", Label).content) == ""

    @pytest.mark.asyncio
    async def test_limpar_global_reseta_firmware(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(FirmwareScreen)
            screen.set_firmware_path("/tmp/fw")
            screen.set_status("Concluído")

            toolbar = app.query_one("#toolbar", Toolbar)
            btn = toolbar.query_one("#tb-clear", Button)
            event = Button.Pressed(btn)
            app.on_button_pressed(event)

            assert screen.get_firmware_path() == ""
            assert str(screen.query_one("#firmware-status", Label).content) == ""

    @pytest.mark.asyncio
    async def test_del_limpa_todos_os_campos(self) -> None:
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one(InstallScreen).set_package_path("/tmp/pkg")
            app.query_one(UpdateScreen).set_package_path("/tmp/upd")
            app.query_one(FirmwareScreen).set_firmware_path("/tmp/fw")

            await pilot.press("delete")

            assert app.query_one(InstallScreen).get_package_path() == ""
            assert app.query_one(UpdateScreen).get_package_path() == ""
            assert app.query_one(FirmwareScreen).get_firmware_path() == ""


class TestSprint1FixesE2E:
    """Testes E2E perspectiva do usuário para as correções do Sprint 1."""

    @pytest.mark.asyncio
    async def test_navbar_exibe_rcm_conectado(self) -> None:
        """Bug 1: usuário vê 'RCM: conectado' na NavBar após polling com Switch conectado."""
        from fusectl.ui.widgets import NavBar

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._sd_paths = []
            app._update_global_status(rcm_connected=True)

            navbar = app.query_one(NavBar)
            assert "conectado" in navbar._status_text

    @pytest.mark.asyncio
    async def test_navbar_exibe_rcm_desconectado(self) -> None:
        """Bug 1: usuário vê 'RCM: desconectado' quando Switch não está em RCM."""
        from fusectl.ui.widgets import NavBar

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._sd_paths = []
            app._update_global_status(rcm_connected=False)

            navbar = app.query_one(NavBar)
            assert "desconectado" in navbar._status_text

    @pytest.mark.asyncio
    async def test_navbar_exibe_nome_sd(self, tmp_path: Path) -> None:
        """Bug 1: usuário vê o nome do ponto de montagem do SD na NavBar."""
        from fusectl.ui.widgets import NavBar

        sd = tmp_path / "meu_sd"
        sd.mkdir()

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app._sd_paths = [sd]
            app._update_global_status(rcm_connected=False)

            navbar = app.query_one(NavBar)
            assert "meu_sd" in navbar._status_text

    @pytest.mark.asyncio
    async def test_navbar_presente_na_tui(self) -> None:
        """Bug 1: NavBar está presente no layout da TUI após a correção."""
        from fusectl.ui.widgets import NavBar

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            assert app.query_one(NavBar) is not None

    @pytest.mark.asyncio
    async def test_payload_selecao_sobrevive_refresh_polling(self) -> None:
        """Bug 4: usuário seleciona payload, polling atualiza lista, seleção permanece."""
        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            rcm = app.query_one(RCMScreen)
            payloads = [Path("/tmp/fusee.bin"), Path("/tmp/tegra.bin"), Path("/tmp/hekate.bin")]
            rcm.update_payloads(payloads)

            ol = rcm.query_one("#payload-list", OptionList)
            ol.highlighted = 2
            assert rcm.get_selected_payload() == Path("/tmp/hekate.bin")

            # simula 3 ciclos de polling sem mudança na lista
            rcm.update_payloads(payloads)
            rcm.update_payloads(payloads)
            rcm.update_payloads(payloads)

            assert rcm.get_selected_payload() == Path("/tmp/hekate.bin")

    @pytest.mark.asyncio
    async def test_install_remove_stale_apg_visivel_no_sd(
        self, cnx_package: Path, sd_card: Path
    ) -> None:
        """Bug 5: após instalar, usuário não tem package3 sem .apg coexistindo no SD."""
        from fusectl.sdcard.installer import install

        (cnx_package / "atmosphere" / "package3").write_bytes(b"\xDE\xAD\xBE\xEF" * 16)
        stale = sd_card / "atmosphere" / "package3"
        stale.write_bytes(b"\x00" * 64)

        app = FuseCtlApp()
        async with app.run_test(size=(120, 40)) as pilot:
            screen = app.query_one(InstallScreen)
            screen.set_package_path(str(cnx_package))
            app._sd_paths = [sd_card]

        # operação real de install (sem mock no shutil)
        errors = install(cnx_package, sd_card)

        assert errors == []
        assert not stale.exists(), "package3 sem .apg não deve existir após install"
        assert (sd_card / "atmosphere" / "package3.apg").is_file()

    @pytest.mark.asyncio
    async def test_update_remove_multiplos_hekate_antigos(
        self, cnx_package: Path, sd_card: Path
    ) -> None:
        """Bug 3: após atualizar, usuário não tem NENHUM hekate_ctcaer_* antigo no SD."""
        from fusectl.sdcard.updater import update

        (sd_card / "hekate_ctcaer_5.9.0_ctcaer_0.6.5.bin").write_bytes(b"\x00")
        (sd_card / "hekate_ctcaer_6.0.1_ctcaer_0.7.0.bin").write_bytes(b"\x00")
        (sd_card / "hekate_ctcaer_6.1.0_ctcaer_0.8.0.bin").write_bytes(b"\x00")

        errors = update(cnx_package, sd_card)

        assert errors == []
        hekate_stale = list(sd_card.glob("hekate_ctcaer_*.bin"))
        assert hekate_stale == [], f"Encontrado hekate antigo: {hekate_stale}"
