"""Unit tests for SSH controller repository."""

from unittest.mock import Mock

import pytest

from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.cache_system import SystemCache
from retromcp.infrastructure.ssh_controller_repository import SSHControllerRepository


@pytest.mark.unit
@pytest.mark.infrastructure
@pytest.mark.ssh_repos
@pytest.mark.controller_repo
class TestSSHControllerRepository:
    """Test SSHControllerRepository."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Provide mocked RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def mock_cache(self) -> Mock:
        """Provide mocked system cache."""
        return Mock(spec=SystemCache)

    @pytest.fixture
    def repository(
        self, mock_client: Mock, mock_cache: Mock
    ) -> SSHControllerRepository:
        """Provide SSH controller repository with mocked client and cache."""
        return SSHControllerRepository(mock_client, mock_cache)

    def test_init(self, mock_client: Mock, mock_cache: Mock) -> None:
        """Test repository initialization."""
        repo = SSHControllerRepository(mock_client, mock_cache)
        assert repo._client == mock_client
        assert repo._cache == mock_cache

    def test_detect_controllers_no_joystick_devices(
        self, repository: SSHControllerRepository, mock_client: Mock, mock_cache: Mock
    ) -> None:
        """Test detect_controllers when no joystick devices are found."""
        # Mock cache to return None (no cached data)
        mock_cache.get_hardware_scan.return_value = None

        # Mock ls command to return no devices, and lsusb command
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="ls -la /dev/input/js* 2>/dev/null",
                exit_code=2,
                stdout="",
                stderr="ls: cannot access '/dev/input/js*': No such file or directory",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="lsusb",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        controllers = repository.detect_controllers()
        assert controllers == []
        assert mock_client.execute_command.call_count == 2

    def test_detect_controllers_single_xbox_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with single Xbox controller."""
        # Mock ls command to return joystick device
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"

        # Mock lsusb command
        usb_output = (
            "Bus 001 Device 003: ID 045e:028e Microsoft Corp. Xbox360 Controller"
        )

        # Mock device name lookup
        name_output = 'N: Name="Xbox 360 Wireless Receiver"'

        # Mock config check (not configured)
        config_result = CommandResult(
            command="grep -q 'input_device.*Xbox 360 Wireless Receiver' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        # Mock xpad driver check (not loaded)
        xpad_result = CommandResult(
            command="lsmod | grep -q xpad",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            xpad_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Xbox 360 Wireless Receiver"
        assert controller.device_path == "/dev/input/js0"
        assert controller.controller_type == ControllerType.XBOX
        assert controller.connected is True
        assert controller.vendor_id == "045e"
        assert controller.product_id == "028e"
        assert controller.is_configured is False
        assert controller.driver_required == "xboxdrv"

    def test_detect_controllers_ps4_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with PS4 controller."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = (
            "Bus 001 Device 003: ID 054c:09cc Sony Corp. Wireless Controller (PS4)"
        )
        name_output = 'N: Name="Sony Wireless Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Sony Wireless Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        ds4_result = CommandResult(
            command="which ds4drv",
            exit_code=0,
            stdout="/usr/local/bin/ds4drv",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            ds4_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Sony Wireless Controller"
        assert controller.controller_type == ControllerType.PS4
        assert controller.connected is True
        assert controller.vendor_id == "054c"
        assert controller.product_id == "09cc"
        assert controller.is_configured is True
        assert controller.driver_required is None

    def test_detect_controllers_ps5_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with PS5 controller."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = (
            "Bus 001 Device 003: ID 054c:0ce6 Sony Corp. DualSense Wireless Controller"
        )
        name_output = 'N: Name="Sony DualSense Wireless Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Sony DualSense Wireless Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Sony DualSense Wireless Controller"
        assert controller.controller_type == ControllerType.PS5
        assert controller.connected is True
        assert controller.vendor_id == "054c"
        assert controller.product_id == "0ce6"
        assert controller.is_configured is False
        assert controller.driver_required is None

    def test_detect_controllers_nintendo_pro_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with Nintendo Pro controller."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 057e:2009 Nintendo Co., Ltd Pro Controller"
        name_output = 'N: Name="Nintendo Switch Pro Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Nintendo Switch Pro Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Nintendo Switch Pro Controller"
        assert controller.controller_type == ControllerType.NINTENDO_PRO
        assert controller.connected is True
        assert controller.vendor_id == "057e"
        assert controller.product_id == "2009"
        assert controller.is_configured is False
        assert controller.driver_required is None

    def test_detect_controllers_8bitdo_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with 8BitDo controller."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 2dc8:6001 8BitDo SN30 Pro"
        name_output = 'N: Name="8BitDo SN30 Pro"'

        config_result = CommandResult(
            command="grep -q 'input_device.*8BitDo SN30 Pro' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "8BitDo SN30 Pro"
        assert controller.controller_type == ControllerType.EIGHT_BIT_DO
        assert controller.connected is True
        assert controller.vendor_id == "2dc8"
        assert controller.product_id == "6001"
        assert controller.is_configured is False
        assert controller.driver_required is None

    def test_detect_controllers_generic_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with generic controller."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 1234:5678 Generic Gamepad"
        name_output = 'N: Name="USB Gamepad"'

        config_result = CommandResult(
            command="grep -q 'input_device.*USB Gamepad' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "USB Gamepad"
        assert controller.controller_type == ControllerType.GENERIC
        assert controller.connected is True
        assert controller.vendor_id == "1234"
        assert controller.product_id == "5678"
        assert controller.is_configured is False
        assert controller.driver_required is None

    def test_detect_controllers_unknown_controller(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with unknown controller (no name found)."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 1234:5678 Generic Gamepad"

        config_result = CommandResult(
            command="grep -q 'input_device.*Unknown Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                "",
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Unknown Controller"
        assert controller.controller_type == ControllerType.UNKNOWN
        assert controller.connected is True
        assert controller.vendor_id == "0000"
        assert controller.product_id == "0000"
        assert controller.is_configured is False
        assert controller.driver_required is None

    def test_detect_controllers_multiple_controllers(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with multiple controllers."""
        js_output = (
            "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0\n"
            "crw-rw---- 1 root input 13, 1 Jan 1 12:00 /dev/input/js1"
        )
        usb_output = (
            "Bus 001 Device 003: ID 045e:028e Microsoft Corp. Xbox360 Controller\n"
            "Bus 001 Device 004: ID 054c:09cc Sony Corp. Wireless Controller (PS4)"
        )

        name_output_0 = 'N: Name="Xbox 360 Wireless Receiver"'
        name_output_1 = 'N: Name="Sony Wireless Controller"'

        config_result_0 = CommandResult(
            command="grep -q 'input_device.*Xbox 360 Wireless Receiver' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        xpad_result = CommandResult(
            command="lsmod | grep -q xpad",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        config_result_1 = CommandResult(
            command="grep -q 'input_device.*Sony Wireless Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        ds4_result = CommandResult(
            command="which ds4drv",
            exit_code=0,
            stdout="/usr/local/bin/ds4drv",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output_0,
                "",
                True,
                0.1,
            ),
            config_result_0,
            xpad_result,
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js1 | grep Name | head -1",
                0,
                name_output_1,
                "",
                True,
                0.1,
            ),
            config_result_1,
            ds4_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 2

        # Xbox controller
        xbox_controller = controllers[0]
        assert xbox_controller.name == "Xbox 360 Wireless Receiver"
        assert xbox_controller.device_path == "/dev/input/js0"
        assert xbox_controller.controller_type == ControllerType.XBOX
        assert xbox_controller.connected is True
        assert xbox_controller.driver_required == "xboxdrv"

        # PS4 controller
        ps4_controller = controllers[1]
        assert ps4_controller.name == "Sony Wireless Controller"
        assert ps4_controller.device_path == "/dev/input/js1"
        assert ps4_controller.controller_type == ControllerType.PS4
        assert ps4_controller.connected is True
        assert ps4_controller.driver_required is None

    def test_detect_controllers_malformed_ls_output(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with malformed ls output."""
        js_output = "invalid output without proper format"

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, "", "", True, 0.1),
        ]

        controllers = repository.detect_controllers()
        assert controllers == []

    def test_detect_controllers_lsusb_failure(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers when lsusb fails."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        name_output = 'N: Name="Xbox 360 Wireless Receiver"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Xbox 360 Wireless Receiver' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        xpad_result = CommandResult(
            command="lsmod | grep -q xpad",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 1, "", "lsusb: error", False, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            xpad_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Xbox 360 Wireless Receiver"
        assert controller.connected is True
        assert controller.vendor_id == "0000"  # Default when lsusb fails
        assert controller.product_id == "0000"

    def test_detect_controllers_name_lookup_failure(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers when name lookup fails."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = (
            "Bus 001 Device 003: ID 045e:028e Microsoft Corp. Xbox360 Controller"
        )

        config_result = CommandResult(
            command="grep -q 'input_device.*Unknown Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                1,
                "",
                "No such device",
                False,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Unknown Controller"
        assert controller.controller_type == ControllerType.UNKNOWN
        assert controller.connected is True

    def test_detect_controllers_no_usb_match(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers when no USB device matches controller keywords."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 1234:5678 Some Random Device"
        name_output = 'N: Name="Test Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Test Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Test Controller"
        assert controller.connected is True
        assert controller.vendor_id == "0000"  # Default when no USB match
        assert controller.product_id == "0000"

    def test_setup_controller_xbox_with_xboxdrv(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller for Xbox controller requiring xboxdrv."""
        controller = Controller(
            name="Xbox 360 Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.XBOX,
            connected=True,
            vendor_id="045e",
            product_id="028e",
            is_configured=False,
            driver_required="xboxdrv",
        )

        expected_command = (
            "sudo apt-get update && "
            "sudo apt-get install -y xboxdrv && "
            "sudo systemctl enable xboxdrv && "
            "sudo systemctl start xboxdrv && "
            "sudo -u pi emulationstation --configure-input /dev/input/js0"
        )

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Setup completed successfully",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        result = repository.setup_controller(controller)

        assert result.success is True
        assert result.stdout == "Setup completed successfully"
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_setup_controller_ps4_with_ds4drv(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller for PS4 controller requiring ds4drv."""
        controller = Controller(
            name="Sony Wireless Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.PS4,
            connected=True,
            vendor_id="054c",
            product_id="09cc",
            is_configured=False,
            driver_required="ds4drv",
        )

        expected_command = (
            "sudo apt-get update && "
            "sudo apt-get install -y python3-pip && "
            "sudo pip3 install ds4drv && "
            "sudo -u pi emulationstation --configure-input /dev/input/js0"
        )

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Setup completed successfully",
            stderr="",
            success=True,
            execution_time=10.0,
        )

        result = repository.setup_controller(controller)

        assert result.success is True
        assert result.stdout == "Setup completed successfully"
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_setup_controller_no_driver_required(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller for controller not requiring special driver."""
        controller = Controller(
            name="Nintendo Switch Pro Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.NINTENDO_PRO,
            connected=True,
            vendor_id="057e",
            product_id="2009",
            is_configured=False,
            driver_required=None,
        )

        expected_command = (
            "sudo -u pi emulationstation --configure-input /dev/input/js0"
        )

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Configuration completed",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        result = repository.setup_controller(controller)

        assert result.success is True
        assert result.stdout == "Configuration completed"
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_setup_controller_already_configured(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller for controller that doesn't need setup."""
        controller = Controller(
            name="Already Configured Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        # Even if no driver is required, EmulationStation config is still needed
        expected_command = (
            "sudo -u pi emulationstation --configure-input /dev/input/js0"
        )

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Configuration completed",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        result = repository.setup_controller(controller)

        assert result.success is True
        assert result.stdout == "Configuration completed"
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_setup_controller_command_failure(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller when command execution fails."""
        controller = Controller(
            name="Xbox 360 Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.XBOX,
            connected=True,
            vendor_id="045e",
            product_id="028e",
            is_configured=False,
            driver_required="xboxdrv",
        )

        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && ...",
            exit_code=1,
            stdout="",
            stderr="Package installation failed",
            success=False,
            execution_time=3.0,
        )

        result = repository.setup_controller(controller)

        assert result.success is False
        assert result.stderr == "Package installation failed"
        assert result.exit_code == 1

    def test_test_controller_success(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test test_controller with successful execution."""
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        expected_command = "timeout 5 jstest --normal /dev/input/js0"

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Driver version is 2.1.0.\nJoystick (Test Controller) has 8 axes",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        result = repository.test_controller(controller)

        assert result.success is True
        assert "Driver version is 2.1.0." in result.stdout
        mock_client.execute_command.assert_called_once_with(expected_command)

    def test_test_controller_failure(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test test_controller with command failure."""
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        expected_command = "timeout 5 jstest --normal /dev/input/js0"

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=1,
            stdout="",
            stderr="jstest: /dev/input/js0: No such file or directory",
            success=False,
            execution_time=0.1,
        )

        result = repository.test_controller(controller)

        assert result.success is False
        assert "No such file or directory" in result.stderr
        mock_client.execute_command.assert_called_once_with(expected_command)

    def test_configure_controller_mapping_success(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test configure_controller_mapping with successful execution."""
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        mapping = {"a_btn": "0", "b_btn": "1", "x_btn": "2", "y_btn": "3"}

        expected_config = (
            'input_device = "Test Controller"\n'
            'input_a_btn = "0"\n'
            'input_b_btn = "1"\n'
            'input_x_btn = "2"\n'
            'input_y_btn = "3"'
        )

        expected_command = f"echo '{expected_config}' > '/opt/retropie/configs/all/retroarch/autoconfig/Test Controller.cfg'"

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.5,
        )

        result = repository.configure_controller_mapping(controller, mapping)

        assert result.success is True
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_configure_controller_mapping_failure(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test configure_controller_mapping with command failure."""
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        mapping = {"a_btn": "0"}

        mock_client.execute_command.return_value = CommandResult(
            command="echo '...' > '/opt/retropie/configs/all/retroarch/autoconfig/Test Controller.cfg'",
            exit_code=1,
            stdout="",
            stderr="Permission denied",
            success=False,
            execution_time=0.1,
        )

        result = repository.configure_controller_mapping(controller, mapping)

        assert result.success is False
        assert result.stderr == "Permission denied"

    def test_configure_controller_mapping_empty_mapping(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test configure_controller_mapping with empty mapping."""
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        mapping = {}

        expected_config = 'input_device = "Test Controller"'
        expected_command = f"echo '{expected_config}' > '/opt/retropie/configs/all/retroarch/autoconfig/Test Controller.cfg'"

        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.5,
        )

        result = repository.configure_controller_mapping(controller, mapping)

        assert result.success is True
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_setup_controller_empty_commands_edge_case(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test setup_controller theoretical edge case with empty commands (though unreachable in current implementation)."""
        # This test documents the unreachable code path at line 169
        # In the current implementation, commands.append() at line 160 always adds EmulationStation config
        # So the empty commands case is never reached, but this test documents that behavior
        controller = Controller(
            name="Test Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.GENERIC,
            connected=True,
            vendor_id="1234",
            product_id="5678",
            is_configured=True,
            driver_required=None,
        )

        # Mock the setup to verify the normal path is always taken
        expected_command = (
            "sudo -u pi emulationstation --configure-input /dev/input/js0"
        )
        mock_client.execute_command.return_value = CommandResult(
            command=expected_command,
            exit_code=0,
            stdout="Configuration completed",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        result = repository.setup_controller(controller)

        # Verify the normal path is taken (not the empty commands path)
        assert result.success is True
        assert result.stdout == "Configuration completed"
        mock_client.execute_command.assert_called_once_with(
            expected_command, use_sudo=True
        )

    def test_detect_controllers_xbox_with_xpad_loaded(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with Xbox controller when xpad driver is already loaded."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = (
            "Bus 001 Device 003: ID 045e:028e Microsoft Corp. Xbox360 Controller"
        )
        name_output = 'N: Name="Xbox 360 Wireless Receiver"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Xbox 360 Wireless Receiver' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        # xpad driver is loaded
        xpad_result = CommandResult(
            command="lsmod | grep -q xpad",
            exit_code=0,
            stdout="xpad                   32768  0",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            xpad_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Xbox 360 Wireless Receiver"
        assert controller.controller_type == ControllerType.XBOX
        assert controller.connected is True
        assert (
            controller.driver_required is None
        )  # No driver required since xpad is loaded

    def test_detect_controllers_ps4_without_ds4drv(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with PS4 controller when ds4drv is not installed."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = (
            "Bus 001 Device 003: ID 054c:09cc Sony Corp. Wireless Controller (PS4)"
        )
        name_output = 'N: Name="Sony Wireless Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*Sony Wireless Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        # ds4drv not installed
        ds4_result = CommandResult(
            command="which ds4drv",
            exit_code=1,
            stdout="",
            stderr="ds4drv: command not found",
            success=False,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            ds4_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "Sony Wireless Controller"
        assert controller.controller_type == ControllerType.PS4
        assert controller.connected is True
        assert controller.driver_required == "ds4drv"

    def test_detect_controllers_edge_case_playstation_detection(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with edge case PlayStation controller names."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/js0"
        usb_output = "Bus 001 Device 003: ID 054c:09cc Sony Corp. Wireless Controller"
        name_output = 'N: Name="DualShock 4 Controller"'

        config_result = CommandResult(
            command="grep -q 'input_device.*DualShock 4 Controller' /opt/retropie/configs/all/retroarch.cfg",
            exit_code=1,
            stdout="",
            stderr="",
            success=False,
            execution_time=0.1,
        )

        ds4_result = CommandResult(
            command="which ds4drv",
            exit_code=0,
            stdout="/usr/local/bin/ds4drv",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
            CommandResult(
                "cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1",
                0,
                name_output,
                "",
                True,
                0.1,
            ),
            config_result,
            ds4_result,
        ]

        controllers = repository.detect_controllers()

        assert len(controllers) == 1
        controller = controllers[0]
        assert controller.name == "DualShock 4 Controller"
        assert controller.controller_type == ControllerType.PS4
        assert controller.connected is True
        assert controller.driver_required is None

    def test_detect_controllers_malformed_device_path(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with malformed device path in ls output."""
        js_output = "crw-rw---- 1 root input 13, 0 Jan 1 12:00 /dev/input/invalid"
        usb_output = "Bus 001 Device 003: ID 1234:5678 Test Device"

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
        ]

        controllers = repository.detect_controllers()

        # Should not create controller for invalid device path
        assert controllers == []

    def test_detect_controllers_short_ls_output(
        self, repository: SSHControllerRepository, mock_client: Mock
    ) -> None:
        """Test detect_controllers with short ls output (less than 9 parts)."""
        js_output = "short output"
        usb_output = "Bus 001 Device 003: ID 1234:5678 Test Device"

        mock_client.execute_command.side_effect = [
            CommandResult(
                "ls -la /dev/input/js* 2>/dev/null", 0, js_output, "", True, 0.1
            ),
            CommandResult("lsusb", 0, usb_output, "", True, 0.1),
        ]

        controllers = repository.detect_controllers()

        # Should not create controller for malformed ls output
        assert controllers == []
