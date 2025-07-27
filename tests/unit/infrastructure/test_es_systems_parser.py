"""Unit tests for ESSystemsConfigParser infrastructure implementation."""

import pytest

from retromcp.domain.models import ESSystemsConfig
from retromcp.domain.models import ValidationError
from retromcp.infrastructure.es_systems_parser import ESSystemsConfigParser


@pytest.mark.unit
@pytest.mark.infrastructure
class TestESSystemsConfigParser:
    """Test cases for ESSystemsConfigParser implementation."""

    @pytest.fixture
    def parser(self) -> ESSystemsConfigParser:
        """Create parser instance for testing."""
        return ESSystemsConfigParser()

    @pytest.fixture
    def valid_single_system_xml(self) -> str:
        """Valid XML with single system definition."""
        return """<?xml version="1.0"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/nes</path>
        <extension>.nes .zip .NES .ZIP</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nes %ROM%</command>
        <platform>nes</platform>
        <theme>nes</theme>
    </system>
</systemList>"""

    @pytest.fixture
    def valid_multiple_systems_xml(self) -> str:
        """Valid XML with multiple system definitions."""
        return """<?xml version="1.0"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/nes</path>
        <extension>.nes .zip .NES .ZIP</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nes %ROM%</command>
        <platform>nes</platform>
        <theme>nes</theme>
    </system>
    <system>
        <name>snes</name>
        <fullname>Super Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/snes</path>
        <extension>.smc .sfc .SMC .SFC</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ snes %ROM%</command>
        <platform>snes</platform>
        <theme>snes</theme>
    </system>
</systemList>"""

    @pytest.fixture
    def minimal_required_fields_xml(self) -> str:
        """Valid XML with only required fields."""
        return """<?xml version="1.0"?>
<systemList>
    <system>
        <name>genesis</name>
        <fullname>Sega Genesis</fullname>
        <path>/home/pi/RetroPie/roms/genesis</path>
        <extension>.gen .md .bin .GEN .MD .BIN</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ genesis %ROM%</command>
    </system>
</systemList>"""

    def test_parser_implements_configuration_parser_interface(self, parser: ESSystemsConfigParser):
        """Test that ESSystemsConfigParser implements ConfigurationParser interface."""
        from retromcp.domain.ports import ConfigurationParser

        # Assert
        assert isinstance(parser, ConfigurationParser)
        assert hasattr(parser, 'parse_es_systems_config')

    def test_parse_valid_single_system_xml(self, parser: ESSystemsConfigParser, valid_single_system_xml: str):
        """Test parsing valid XML with single system definition."""
        # Act
        result = parser.parse_es_systems_config(valid_single_system_xml)

        # Assert
        assert result.is_success()
        config = result.success_value
        assert isinstance(config, ESSystemsConfig)
        assert len(config.systems) == 1

        system = config.systems[0]
        assert system.name == "nes"
        assert system.fullname == "Nintendo Entertainment System"
        assert system.path == "/home/pi/RetroPie/roms/nes"
        assert system.extensions == [".nes", ".zip", ".NES", ".ZIP"]
        assert "/opt/retropie/supplementary/runcommand/runcommand.sh" in system.command
        assert system.platform == "nes"
        assert system.theme == "nes"

    def test_parse_valid_multiple_systems_xml(self, parser: ESSystemsConfigParser, valid_multiple_systems_xml: str):
        """Test parsing valid XML with multiple system definitions."""
        # Act
        result = parser.parse_es_systems_config(valid_multiple_systems_xml)

        # Assert
        assert result.is_success()
        config = result.success_value
        assert isinstance(config, ESSystemsConfig)
        assert len(config.systems) == 2

        # Check NES system
        nes_system = config.systems[0]
        assert nes_system.name == "nes"
        assert nes_system.fullname == "Nintendo Entertainment System"
        assert nes_system.extensions == [".nes", ".zip", ".NES", ".ZIP"]

        # Check SNES system
        snes_system = config.systems[1]
        assert snes_system.name == "snes"
        assert snes_system.fullname == "Super Nintendo Entertainment System"
        assert snes_system.extensions == [".smc", ".sfc", ".SMC", ".SFC"]

    def test_parse_minimal_required_fields_xml(self, parser: ESSystemsConfigParser, minimal_required_fields_xml: str):
        """Test parsing XML with only required fields (optional fields should be None)."""
        # Act
        result = parser.parse_es_systems_config(minimal_required_fields_xml)

        # Assert
        assert result.is_success()
        config = result.success_value
        assert len(config.systems) == 1

        system = config.systems[0]
        assert system.name == "genesis"
        assert system.fullname == "Sega Genesis"
        assert system.path == "/home/pi/RetroPie/roms/genesis"
        assert system.extensions == [".gen", ".md", ".bin", ".GEN", ".MD", ".BIN"]
        assert "/opt/retropie/supplementary/runcommand/runcommand.sh" in system.command
        assert system.platform is None  # Optional field not present
        assert system.theme is None      # Optional field not present

    def test_parse_empty_system_list_xml(self, parser: ESSystemsConfigParser):
        """Test parsing XML with empty system list."""
        # Arrange
        empty_xml = """<?xml version="1.0"?>
<systemList>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(empty_xml)

        # Assert
        assert result.is_success()
        config = result.success_value
        assert isinstance(config, ESSystemsConfig)
        assert len(config.systems) == 0
        assert config.systems == []

    def test_parse_malformed_xml_fails(self, parser: ESSystemsConfigParser):
        """Test that malformed XML returns validation error."""
        # Arrange
        malformed_xml = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System
        <!-- Missing closing tag -->
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(malformed_xml)

        # Assert
        assert result.is_error()
        error = result.error_value
        assert isinstance(error, ValidationError)
        assert "XML" in error.message or "parse" in error.message.lower()

    def test_parse_missing_required_field_fails(self, parser: ESSystemsConfigParser):
        """Test that missing required fields returns validation error."""
        # Arrange - Missing 'name' field
        missing_name_xml = """<?xml version="1.0"?>
<systemList>
    <system>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/nes</path>
        <extension>.nes .zip</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(missing_name_xml)

        # Assert
        assert result.is_error()
        error = result.error_value
        assert isinstance(error, ValidationError)
        assert "required" in error.message.lower() or "missing" in error.message.lower()

    def test_parse_invalid_xml_structure_fails(self, parser: ESSystemsConfigParser):
        """Test that invalid XML structure returns validation error."""
        # Arrange - Wrong root element
        invalid_structure_xml = """<?xml version="1.0"?>
<wrongRoot>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/nes</path>
        <extension>.nes .zip</extension>
        <command>test command</command>
    </system>
</wrongRoot>"""

        # Act
        result = parser.parse_es_systems_config(invalid_structure_xml)

        # Assert
        assert result.is_error()
        error = result.error_value
        assert isinstance(error, ValidationError)
        assert "systemList" in error.message or "structure" in error.message.lower()

    def test_parse_non_xml_content_fails(self, parser: ESSystemsConfigParser):
        """Test that non-XML content returns validation error."""
        # Arrange
        non_xml_content = "This is not XML content at all!"

        # Act
        result = parser.parse_es_systems_config(non_xml_content)

        # Assert
        assert result.is_error()
        error = result.error_value
        assert isinstance(error, ValidationError)
        assert "XML" in error.message or "parse" in error.message.lower()

    def test_parse_extension_list_correctly_splits_on_spaces(self, parser: ESSystemsConfigParser):
        """Test that extensions are correctly split on spaces."""
        # Arrange
        xml_with_extensions = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test System</fullname>
        <path>/test/path</path>
        <extension>.ext1 .ext2 .EXT1 .EXT2 .ext3</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_extensions)

        # Assert
        assert result.is_success()
        system = result.success_value.systems[0]
        expected_extensions = [".ext1", ".ext2", ".EXT1", ".EXT2", ".ext3"]
        assert system.extensions == expected_extensions

    def test_parse_whitespace_handling_in_extensions(self, parser: ESSystemsConfigParser):
        """Test that whitespace in extensions is handled correctly."""
        # Arrange
        xml_with_whitespace = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test System</fullname>
        <path>/test/path</path>
        <extension>  .ext1   .ext2  .ext3  </extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_whitespace)

        # Assert
        assert result.is_success()
        system = result.success_value.systems[0]
        # Should handle leading/trailing whitespace and multiple spaces
        expected_extensions = [".ext1", ".ext2", ".ext3"]
        assert system.extensions == expected_extensions

    def test_parse_empty_string_returns_validation_error(self, parser: ESSystemsConfigParser):
        """Test that empty string returns validation error."""
        # Act
        result = parser.parse_es_systems_config("")

        # Assert
        assert result.is_error()
        error = result.error_value
        assert isinstance(error, ValidationError)

    def test_parse_multiple_platforms_preserved(self, parser: ESSystemsConfigParser):
        """Test that multiple platforms in platform field are preserved as string."""
        # Arrange
        xml_with_multiple_platforms = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>genesis</name>
        <fullname>Sega Genesis/Mega Drive</fullname>
        <path>/home/pi/RetroPie/roms/genesis</path>
        <extension>.gen .md .bin</extension>
        <command>test command</command>
        <platform>genesis, megadrive</platform>
        <theme>genesis</theme>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_multiple_platforms)

        # Assert
        assert result.is_success()
        system = result.success_value.systems[0]
        assert system.platform == "genesis, megadrive"

    def test_parse_required_field_with_empty_element_text(self, parser: ESSystemsConfigParser):
        """Test that fields with empty text content are treated as missing."""
        # Arrange
        xml_with_empty_name = """<?xml version="1.0"?>
<systemList>
    <system>
        <name></name>
        <fullname>Test System</fullname>
        <path>/test/path</path>
        <extension>.test</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_empty_name)
        
        # Assert
        assert result.is_error()
        assert result.error_value.code == "MISSING_REQUIRED_FIELD"
        assert "name" in result.error_value.message

    def test_parse_required_field_with_whitespace_only(self, parser: ESSystemsConfigParser):
        """Test that fields containing only whitespace are treated as missing."""
        # Arrange
        xml_with_whitespace_fullname = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>   
        
        </fullname>
        <path>/test/path</path>
        <extension>.test</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_whitespace_fullname)
        
        # Assert
        assert result.is_error()
        assert result.error_value.code == "MISSING_REQUIRED_FIELD"
        assert "fullname" in result.error_value.message

    def test_parse_self_closing_empty_tags(self, parser: ESSystemsConfigParser):
        """Test that self-closing empty tags are treated as missing fields."""
        # Arrange
        xml_with_self_closing = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test System</fullname>
        <path />
        <extension>.test</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_self_closing)
        
        # Assert
        assert result.is_error()
        assert result.error_value.code == "MISSING_REQUIRED_FIELD"
        assert "path" in result.error_value.message

    def test_parse_handles_unexpected_exception_during_parsing(self, parser: ESSystemsConfigParser):
        """Test that unexpected exceptions are caught and converted to ValidationError."""
        # Arrange - Create XML that will cause an unexpected error
        # We'll patch the internal parsing to raise an unexpected exception
        from unittest.mock import patch
        
        valid_xml = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test</fullname>
        <path>/test</path>
        <extension>.test</extension>
        <command>test</command>
    </system>
</systemList>"""
        
        # Patch the parser's method to raise unexpected error
        with patch.object(parser, '_parse_system_definition', side_effect=RuntimeError("Unexpected error")):
            # Act
            result = parser.parse_es_systems_config(valid_xml)
        
            # Assert
            assert result.is_error()
            assert result.error_value.code == "UNEXPECTED_ERROR"
            assert "Unexpected error" in result.error_value.message

    def test_parse_handles_unexpected_exception_in_system_parsing(self, parser: ESSystemsConfigParser):
        """Test that unexpected exceptions in system parsing are caught."""
        # Arrange
        from unittest.mock import patch
        
        xml_content = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test System</fullname>
        <path>/test</path>
        <extension>.test</extension>
        <command>test command</command>
    </system>
</systemList>"""
        
        # Patch _get_required_text to raise an unexpected exception
        with patch.object(parser, '_get_required_text', side_effect=AttributeError("Unexpected attribute error")):
            # Act
            result = parser.parse_es_systems_config(xml_content)
            
            # Assert  
            assert result.is_error()
            assert result.error_value.code == "SYSTEM_PARSE_ERROR"
            assert "Unexpected attribute error" in result.error_value.message

    def test_parse_large_file_with_many_systems(self, parser: ESSystemsConfigParser):
        """Test parsing performance and correctness with many system definitions."""
        # Arrange - Generate XML with 100 systems (not 1000 to keep tests fast)
        systems = []
        for i in range(100):
            systems.append(f"""
    <system>
        <name>system{i}</name>
        <fullname>System {i}</fullname>
        <path>/home/pi/RetroPie/roms/system{i}</path>
        <extension>.ext{i} .zip .7z</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ system{i} %ROM%</command>
        <platform>platform{i}</platform>
        <theme>theme{i}</theme>
    </system>""")
        
        large_xml = f"""<?xml version="1.0"?>
<systemList>
    {''.join(systems)}
</systemList>"""
        
        # Act
        import time
        start = time.time()
        result = parser.parse_es_systems_config(large_xml)
        elapsed = time.time() - start
        
        # Assert
        assert result.is_success()
        config = result.success_value
        assert len(config.systems) == 100
        # Verify first and last systems
        assert config.systems[0].name == "system0"
        assert config.systems[99].name == "system99"
        # Should parse quickly
        assert elapsed < 0.5  # 500ms for 100 systems is reasonable

    def test_parse_xml_with_special_characters_in_paths(self, parser: ESSystemsConfigParser):
        """Test parsing handles special characters in paths and commands."""
        # Arrange - Use &amp; for ampersand in XML
        xml_with_special_chars = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname>Test System with Special Chars</fullname>
        <path>/home/pi/RetroPie/roms/test system &amp; games</path>
        <extension>.test .zip</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ "test system" %ROM%</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_special_chars)
        
        # Assert
        assert result.is_success()
        system = result.success_value.systems[0]
        assert "test system & games" in system.path  # XML parser converts &amp; to &
        assert '"test system"' in system.command

    def test_parse_xml_with_cdata_sections(self, parser: ESSystemsConfigParser):
        """Test parsing handles CDATA sections in fields."""
        # Arrange
        xml_with_cdata = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>test</name>
        <fullname><![CDATA[Test System with <special> characters]]></fullname>
        <path>/test/path</path>
        <extension>.test</extension>
        <command><![CDATA[/bin/sh -c "echo 'test' && run"]]></command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_cdata)
        
        # Assert
        assert result.is_success()
        system = result.success_value.systems[0]
        assert system.fullname == "Test System with <special> characters"
        assert system.command == '/bin/sh -c "echo \'test\' && run"'

    def test_parse_duplicate_system_names_allowed(self, parser: ESSystemsConfigParser):
        """Test that duplicate system names are allowed (common in multi-region setups)."""
        # Arrange
        xml_with_duplicates = """<?xml version="1.0"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System (USA)</fullname>
        <path>/home/pi/RetroPie/roms/nes-usa</path>
        <extension>.nes .zip</extension>
        <command>test command</command>
    </system>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System (Japan)</fullname>
        <path>/home/pi/RetroPie/roms/nes-jpn</path>
        <extension>.nes .fds .zip</extension>
        <command>test command</command>
    </system>
</systemList>"""

        # Act
        result = parser.parse_es_systems_config(xml_with_duplicates)
        
        # Assert
        assert result.is_success()
        config = result.success_value
        assert len(config.systems) == 2
        assert all(s.name == "nes" for s in config.systems)
        assert config.systems[0].path != config.systems[1].path
