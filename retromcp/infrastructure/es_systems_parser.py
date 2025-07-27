"""ESSystemsConfigParser implementation for parsing es_systems.cfg XML files."""

import xml.etree.ElementTree as ET
from typing import List
from typing import Optional

from ..domain.models import ESSystemsConfig
from ..domain.models import Result
from ..domain.models import SystemDefinition
from ..domain.models import ValidationError
from ..domain.ports import ConfigurationParser


class ESSystemsConfigParser(ConfigurationParser):
    """Parser for EmulationStation es_systems.cfg XML configuration files."""

    def parse_es_systems_config(
        self, content: str
    ) -> Result[ESSystemsConfig, ValidationError]:
        """Parse es_systems.cfg XML content into domain models.

        Args:
            content: Raw XML content from es_systems.cfg file

        Returns:
            Result containing parsed ESSystemsConfig or ValidationError
        """
        if not content or not content.strip():
            return Result.error(
                ValidationError(
                    code="EMPTY_CONTENT",
                    message="Empty or whitespace-only content provided",
                )
            )

        try:
            # Parse XML content
            root = ET.fromstring(content)

            # Validate root element
            if root.tag != "systemList":
                return Result.error(
                    ValidationError(
                        code="INVALID_ROOT_ELEMENT",
                        message=f"Expected root element 'systemList', found '{root.tag}'",
                    )
                )

            # Parse all system definitions
            systems: List[SystemDefinition] = []
            for system_element in root.findall("system"):
                system_result = self._parse_system_definition(system_element)
                if system_result.is_error():
                    return Result.error(system_result.error_value)

                systems.append(system_result.success_value)

            # Return successful result
            config = ESSystemsConfig(systems=systems)
            return Result.success(config)

        except ET.ParseError as e:
            return Result.error(
                ValidationError(
                    code="XML_PARSE_ERROR",
                    message=f"Failed to parse XML content: {e!s}",
                )
            )
        except Exception as e:
            return Result.error(
                ValidationError(
                    code="UNEXPECTED_ERROR",
                    message=f"Unexpected error during parsing: {e!s}",
                )
            )

    def _parse_system_definition(
        self, system_element: ET.Element
    ) -> Result[SystemDefinition, ValidationError]:
        """Parse a single system definition from XML element.

        Args:
            system_element: XML element containing system definition

        Returns:
            Result containing parsed SystemDefinition or ValidationError
        """
        try:
            # Extract required fields
            name = self._get_required_text(system_element, "name")
            if not name:
                return Result.error(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message="Missing required field 'name'",
                    )
                )

            fullname = self._get_required_text(system_element, "fullname")
            if not fullname:
                return Result.error(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message="Missing required field 'fullname'",
                    )
                )

            path = self._get_required_text(system_element, "path")
            if not path:
                return Result.error(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message="Missing required field 'path'",
                    )
                )

            extension_text = self._get_required_text(system_element, "extension")
            if not extension_text:
                return Result.error(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message="Missing required field 'extension'",
                    )
                )

            command = self._get_required_text(system_element, "command")
            if not command:
                return Result.error(
                    ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message="Missing required field 'command'",
                    )
                )

            # Parse extensions (space-separated)
            extensions = self._parse_extensions(extension_text)

            # Extract optional fields
            platform = self._get_optional_text(system_element, "platform")
            theme = self._get_optional_text(system_element, "theme")

            # Create system definition
            system_def = SystemDefinition(
                name=name,
                fullname=fullname,
                path=path,
                extensions=extensions,
                command=command,
                platform=platform,
                theme=theme,
            )

            return Result.success(system_def)

        except Exception as e:
            return Result.error(
                ValidationError(
                    code="SYSTEM_PARSE_ERROR",
                    message=f"Failed to parse system definition: {e!s}",
                )
            )

    def _get_required_text(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """Get text content from required XML element.

        Args:
            parent: Parent XML element
            tag_name: Name of the child element to find

        Returns:
            Text content or None if element not found or empty
        """
        element = parent.find(tag_name)
        if element is None:
            return None

        text = element.text
        if text is None:
            return None

        # Return stripped text, None if empty after stripping
        stripped = text.strip()
        return stripped if stripped else None

    def _get_optional_text(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """Get text content from optional XML element.

        Args:
            parent: Parent XML element
            tag_name: Name of the child element to find

        Returns:
            Text content or None if element not found or empty
        """
        # Same implementation as required, but None is acceptable
        return self._get_required_text(parent, tag_name)

    def _parse_extensions(self, extension_text: str) -> List[str]:
        """Parse space-separated extensions into a list.

        Args:
            extension_text: Space-separated extension string like ".nes .zip .NES .ZIP"

        Returns:
            List of individual extensions
        """
        # Split on whitespace and filter out empty strings
        extensions = []
        for ext in extension_text.split():
            ext = ext.strip()
            if ext:
                extensions.append(ext)

        return extensions
