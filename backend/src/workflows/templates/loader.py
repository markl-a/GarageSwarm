"""
Workflow Template Loader

Loads, parses, and validates YAML workflow templates.
Supports template discovery, caching, and conversion to WorkflowGraph.
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field, validator

from ..graph import WorkflowGraph
from ..nodes import NodeType, create_node


class TemplateValidationError(Exception):
    """Exception raised when template validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Template validation failed: {'; '.join(errors)}")


class TemplateMetadata(BaseModel):
    """
    Metadata for a workflow template.

    Contains identifying information and schema details.
    """
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"

    # Input schema for template parameters
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    # Categorization
    tags: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Source information
    source_path: Optional[str] = None

    # Author information
    author: Optional[str] = None

    class Config:
        extra = "allow"

    @validator("id", pre=True, always=True)
    def validate_id(cls, v):
        """Ensure ID is a valid identifier."""
        if v and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("ID must contain only alphanumeric characters, underscores, and hyphens")
        return v


class CachedTemplate:
    """
    Cached template with metadata and content hash.
    """

    def __init__(
        self,
        metadata: TemplateMetadata,
        raw_content: Dict[str, Any],
        content_hash: str,
        loaded_at: datetime
    ):
        self.metadata = metadata
        self.raw_content = raw_content
        self.content_hash = content_hash
        self.loaded_at = loaded_at


class TemplateLoader:
    """
    Workflow template loader and parser.

    Features:
    - Discovers templates from the templates directory
    - Parses YAML templates
    - Validates template structure
    - Creates WorkflowGraph from templates
    - Caches loaded templates

    Usage:
        loader = TemplateLoader("/path/to/templates")

        # List available templates
        templates = loader.list_templates()

        # Load and create workflow
        workflow = loader.create_workflow_from_template(
            "my-template",
            {"input_param": "value"}
        )
    """

    # Required fields in template
    REQUIRED_FIELDS = {"id", "name", "nodes"}

    # Valid node types
    VALID_NODE_TYPES = {nt.value for nt in NodeType}

    def __init__(
        self,
        templates_dir: Optional[Union[str, Path]] = None,
        cache_enabled: bool = True
    ):
        """
        Initialize template loader.

        Args:
            templates_dir: Directory containing YAML templates.
                          Defaults to 'templates/' in the workflows package.
            cache_enabled: Whether to cache loaded templates.
        """
        if templates_dir is None:
            # Default to templates/ directory relative to this file
            self.templates_dir = Path(__file__).parent / "definitions"
        else:
            self.templates_dir = Path(templates_dir)

        self.cache_enabled = cache_enabled
        self._cache: Dict[str, CachedTemplate] = {}

        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_file_mtime(self, path: Path) -> Optional[datetime]:
        """Get file modification time."""
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return None

    def _discover_template_files(self) -> List[Path]:
        """
        Discover all YAML template files in the templates directory.

        Returns:
            List of paths to template files.
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        # Support both .yaml and .yml extensions
        for pattern in ["*.yaml", "*.yml"]:
            templates.extend(self.templates_dir.glob(pattern))
            # Also search subdirectories
            templates.extend(self.templates_dir.glob(f"**/{pattern}"))

        return sorted(set(templates))

    def _parse_yaml(self, path: Path) -> Dict[str, Any]:
        """
        Parse YAML file and return content.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML content as dictionary.

        Raises:
            ValueError: If file cannot be parsed.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                return {}

            if not isinstance(content, dict):
                raise ValueError(f"Template must be a dictionary, got {type(content).__name__}")

            return content
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}")

    def _extract_metadata(
        self,
        content: Dict[str, Any],
        source_path: Optional[str] = None
    ) -> TemplateMetadata:
        """
        Extract metadata from template content.

        Args:
            content: Parsed template content.
            source_path: Path to template file.

        Returns:
            TemplateMetadata instance.
        """
        metadata_section = content.get("metadata", {})

        return TemplateMetadata(
            id=content.get("id", metadata_section.get("id", "")),
            name=content.get("name", metadata_section.get("name", "")),
            description=content.get("description", metadata_section.get("description", "")),
            version=content.get("version", metadata_section.get("version", "1.0.0")),
            input_schema=content.get("input_schema", metadata_section.get("input_schema", {})),
            tags=content.get("tags", metadata_section.get("tags", [])),
            author=content.get("author", metadata_section.get("author")),
            created_at=metadata_section.get("created_at"),
            updated_at=metadata_section.get("updated_at"),
            source_path=source_path
        )

    def validate_template(self, template_path: Union[str, Path]) -> List[str]:
        """
        Validate a template file.

        Performs comprehensive validation including:
        - Required fields check
        - Node type validation
        - Edge connectivity validation
        - Input schema validation

        Args:
            template_path: Path to template file.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        path = Path(template_path)

        # Check file exists
        if not path.exists():
            return [f"Template file not found: {path}"]

        # Parse YAML
        try:
            content = self._parse_yaml(path)
        except ValueError as e:
            return [str(e)]

        # Validate content structure
        errors.extend(self._validate_content(content))

        return errors

    def _validate_content(self, content: Dict[str, Any]) -> List[str]:
        """
        Validate template content structure.

        Args:
            content: Parsed template content.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []

        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(content.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")

        # Validate ID format
        template_id = content.get("id", "")
        if template_id:
            if not template_id.replace("_", "").replace("-", "").isalnum():
                errors.append(f"Invalid template ID format: {template_id}")
        else:
            errors.append("Template ID is required")

        # Validate name
        if not content.get("name"):
            errors.append("Template name is required")

        # Validate nodes
        nodes = content.get("nodes", [])
        if not nodes:
            errors.append("At least one node is required")
        else:
            node_errors = self._validate_nodes(nodes)
            errors.extend(node_errors)

        # Validate edges
        edges = content.get("edges", [])
        if edges:
            edge_errors = self._validate_edges(edges, nodes)
            errors.extend(edge_errors)

        # Validate input schema
        input_schema = content.get("input_schema", {})
        if input_schema:
            schema_errors = self._validate_input_schema(input_schema)
            errors.extend(schema_errors)

        return errors

    def _validate_nodes(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """
        Validate node definitions.

        Args:
            nodes: List of node definitions.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []
        seen_ids: Set[str] = set()

        if not isinstance(nodes, list):
            return ["Nodes must be a list"]

        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"Node {i} must be a dictionary")
                continue

            # Check required node fields
            node_id = node.get("id")
            if not node_id:
                errors.append(f"Node {i} missing required field: id")
            elif node_id in seen_ids:
                errors.append(f"Duplicate node ID: {node_id}")
            else:
                seen_ids.add(node_id)

            if not node.get("name"):
                errors.append(f"Node {node_id or i} missing required field: name")

            # Validate node type
            node_type = node.get("node_type", node.get("type", "task"))
            if node_type not in self.VALID_NODE_TYPES:
                errors.append(f"Node {node_id or i} has invalid type: {node_type}")

            # Type-specific validation
            type_errors = self._validate_node_type_specific(node, node_type)
            errors.extend(type_errors)

        return errors

    def _validate_node_type_specific(
        self,
        node: Dict[str, Any],
        node_type: str
    ) -> List[str]:
        """
        Validate node type-specific fields.

        Args:
            node: Node definition.
            node_type: Type of the node.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []
        node_id = node.get("id", "unknown")

        if node_type == "condition":
            if not node.get("conditions") and not node.get("true_branch"):
                errors.append(f"Condition node {node_id} should define conditions or branches")

        elif node_type == "parallel":
            branches = node.get("branches", [])
            if not branches:
                errors.append(f"Parallel node {node_id} must define branches")

        elif node_type == "join":
            join_mode = node.get("join_mode", "all")
            if join_mode not in {"all", "any", "n_of_m"}:
                errors.append(f"Join node {node_id} has invalid join_mode: {join_mode}")

        elif node_type == "loop":
            if not node.get("body_node"):
                errors.append(f"Loop node {node_id} must define body_node")

        elif node_type == "subflow":
            if not node.get("workflow_id") and not node.get("workflow_template"):
                errors.append(f"Subflow node {node_id} must define workflow_id or workflow_template")

        elif node_type == "router":
            if not node.get("routes"):
                errors.append(f"Router node {node_id} should define routes")

        return errors

    def _validate_edges(
        self,
        edges: List[Dict[str, str]],
        nodes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Validate edge definitions.

        Args:
            edges: List of edge definitions.
            nodes: List of node definitions.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []

        # Get all node IDs
        node_ids = {node.get("id") for node in nodes if node.get("id")}

        if not isinstance(edges, list):
            return ["Edges must be a list"]

        for i, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"Edge {i} must be a dictionary")
                continue

            # Support both "from"/"to" and "source"/"target" formats
            from_node = edge.get("from") or edge.get("source")
            to_node = edge.get("to") or edge.get("target")

            if not from_node:
                errors.append(f"Edge {i} missing source node (from/source)")
            elif from_node not in node_ids:
                errors.append(f"Edge {i} references non-existent source node: {from_node}")

            if not to_node:
                errors.append(f"Edge {i} missing target node (to/target)")
            elif to_node not in node_ids:
                errors.append(f"Edge {i} references non-existent target node: {to_node}")

        return errors

    def _validate_input_schema(self, schema: Dict[str, Any]) -> List[str]:
        """
        Validate input schema definition.

        Args:
            schema: Input schema definition.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []

        if not isinstance(schema, dict):
            return ["Input schema must be a dictionary"]

        # Validate each field in schema
        for field_name, field_def in schema.items():
            if not isinstance(field_def, dict):
                errors.append(f"Input schema field '{field_name}' must be a dictionary")
                continue

            # Check for type definition
            field_type = field_def.get("type")
            if field_type:
                valid_types = {"string", "number", "integer", "boolean", "array", "object"}
                if field_type not in valid_types:
                    errors.append(f"Input schema field '{field_name}' has invalid type: {field_type}")

        return errors

    def load_template(self, template_id: str) -> WorkflowGraph:
        """
        Load a template by ID and return a WorkflowGraph.

        Args:
            template_id: ID of the template to load.

        Returns:
            WorkflowGraph instance.

        Raises:
            FileNotFoundError: If template not found.
            TemplateValidationError: If template is invalid.
        """
        # Check cache first
        if self.cache_enabled and template_id in self._cache:
            cached = self._cache[template_id]
            # Verify cache is still valid
            if cached.metadata.source_path:
                path = Path(cached.metadata.source_path)
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        current_hash = self._compute_hash(f.read())
                    if current_hash == cached.content_hash:
                        return self._build_graph_from_content(cached.raw_content)

        # Find template file
        template_path = self._find_template_file(template_id)
        if not template_path:
            raise FileNotFoundError(f"Template not found: {template_id}")

        # Validate template
        errors = self.validate_template(template_path)
        if errors:
            raise TemplateValidationError(errors)

        # Load and parse
        with open(template_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        content = yaml.safe_load(raw_content)

        # Cache the template
        if self.cache_enabled:
            metadata = self._extract_metadata(content, str(template_path))
            self._cache[template_id] = CachedTemplate(
                metadata=metadata,
                raw_content=content,
                content_hash=self._compute_hash(raw_content),
                loaded_at=datetime.utcnow()
            )

        return self._build_graph_from_content(content)

    def _find_template_file(self, template_id: str) -> Optional[Path]:
        """
        Find template file by ID.

        Args:
            template_id: Template ID to find.

        Returns:
            Path to template file or None.
        """
        # Try direct file names
        for ext in [".yaml", ".yml"]:
            path = self.templates_dir / f"{template_id}{ext}"
            if path.exists():
                return path

        # Search all templates for matching ID
        for path in self._discover_template_files():
            try:
                content = self._parse_yaml(path)
                if content.get("id") == template_id:
                    return path
            except ValueError:
                continue

        return None

    def _build_graph_from_content(self, content: Dict[str, Any]) -> WorkflowGraph:
        """
        Build WorkflowGraph from template content.

        Args:
            content: Parsed template content.

        Returns:
            WorkflowGraph instance.
        """
        graph = WorkflowGraph(
            id=content.get("id", ""),
            name=content.get("name", ""),
            description=content.get("description", "")
        )

        # Add nodes
        nodes = content.get("nodes", [])
        for node_data in nodes:
            node_type = node_data.pop("node_type", node_data.pop("type", "task"))
            node = create_node(node_type, **node_data)
            graph.add_node(node)

        # Add edges
        edges = content.get("edges", [])
        for edge in edges:
            from_node = edge.get("from") or edge.get("source")
            to_node = edge.get("to") or edge.get("target")
            if from_node and to_node:
                graph.add_edge(from_node, to_node)

        # Also process next_nodes defined in node data
        for node_data in content.get("nodes", []):
            node_id = node_data.get("id")
            next_nodes = node_data.get("next_nodes", [])
            for next_node in next_nodes:
                if next_node in graph.nodes:
                    try:
                        graph.add_edge(node_id, next_node)
                    except ValueError:
                        pass  # Edge might already exist

        # Set entry and exit nodes
        entry_node = content.get("entry_node")
        if entry_node:
            graph.entry_node = entry_node

        exit_nodes = content.get("exit_nodes", [])
        if exit_nodes:
            graph.exit_nodes = exit_nodes
        else:
            # Auto-detect exit nodes (nodes with no outgoing edges)
            graph.exit_nodes = graph.get_leaf_nodes()

        return graph

    def list_templates(self) -> List[TemplateMetadata]:
        """
        List all available templates.

        Returns:
            List of TemplateMetadata for all discovered templates.
        """
        templates = []

        for path in self._discover_template_files():
            try:
                content = self._parse_yaml(path)
                metadata = self._extract_metadata(content, str(path))

                # Set timestamps from file if not in content
                if not metadata.created_at:
                    metadata.created_at = self._get_file_mtime(path)
                if not metadata.updated_at:
                    metadata.updated_at = self._get_file_mtime(path)

                templates.append(metadata)
            except ValueError:
                # Skip invalid templates
                continue

        return templates

    def get_template_metadata(self, template_id: str) -> TemplateMetadata:
        """
        Get metadata for a specific template.

        Args:
            template_id: ID of the template.

        Returns:
            TemplateMetadata instance.

        Raises:
            FileNotFoundError: If template not found.
        """
        # Check cache
        if self.cache_enabled and template_id in self._cache:
            return self._cache[template_id].metadata

        # Find and load template
        template_path = self._find_template_file(template_id)
        if not template_path:
            raise FileNotFoundError(f"Template not found: {template_id}")

        content = self._parse_yaml(template_path)
        metadata = self._extract_metadata(content, str(template_path))

        # Set timestamps from file
        if not metadata.created_at:
            metadata.created_at = self._get_file_mtime(template_path)
        if not metadata.updated_at:
            metadata.updated_at = self._get_file_mtime(template_path)

        return metadata

    def create_workflow_from_template(
        self,
        template_id: str,
        input_data: Dict[str, Any]
    ) -> WorkflowGraph:
        """
        Create a workflow instance from a template with input data.

        This method:
        1. Loads the template
        2. Validates input data against input schema
        3. Applies input data to the workflow
        4. Returns a configured WorkflowGraph

        Args:
            template_id: ID of the template to use.
            input_data: Input data to populate the workflow.

        Returns:
            Configured WorkflowGraph instance.

        Raises:
            FileNotFoundError: If template not found.
            TemplateValidationError: If template or input is invalid.
        """
        # Load the template
        graph = self.load_template(template_id)

        # Get metadata for input validation
        metadata = self.get_template_metadata(template_id)

        # Validate input data
        input_errors = self._validate_input_data(input_data, metadata.input_schema)
        if input_errors:
            raise TemplateValidationError(input_errors)

        # Generate unique workflow ID
        import uuid
        workflow_id = f"{template_id}_{uuid.uuid4().hex[:8]}"

        # Create new graph with unique ID
        workflow_graph = WorkflowGraph(
            id=workflow_id,
            name=f"{graph.name} (Instance)",
            description=graph.description
        )

        # Copy nodes with input data substitution
        for node_id, node in graph.nodes.items():
            # Clone the node
            node_dict = node.model_dump()

            # Apply input substitution to node configuration
            node_dict = self._substitute_inputs(node_dict, input_data)

            # Create new node
            node_type = node_dict.pop("node_type", NodeType.TASK)
            new_node = create_node(node_type, **node_dict)
            workflow_graph.add_node(new_node)

        # Copy edges
        for from_node, to_nodes in graph.edges.items():
            for to_node in to_nodes:
                workflow_graph.add_edge(from_node, to_node)

        # Copy entry/exit
        workflow_graph.entry_node = graph.entry_node
        workflow_graph.exit_nodes = graph.exit_nodes.copy()

        return workflow_graph

    def _validate_input_data(
        self,
        input_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[str]:
        """
        Validate input data against schema.

        Args:
            input_data: Input data to validate.
            schema: Input schema definition.

        Returns:
            List of validation errors.
        """
        errors: List[str] = []

        if not schema:
            return errors

        for field_name, field_def in schema.items():
            if not isinstance(field_def, dict):
                continue

            # Check required fields
            is_required = field_def.get("required", False)
            if is_required and field_name not in input_data:
                errors.append(f"Missing required input field: {field_name}")
                continue

            if field_name not in input_data:
                continue

            value = input_data[field_name]

            # Type validation
            expected_type = field_def.get("type")
            if expected_type:
                type_valid = self._validate_type(value, expected_type)
                if not type_valid:
                    errors.append(
                        f"Input field '{field_name}' has invalid type: "
                        f"expected {expected_type}, got {type(value).__name__}"
                    )

            # Enum validation
            enum_values = field_def.get("enum")
            if enum_values and value not in enum_values:
                errors.append(
                    f"Input field '{field_name}' must be one of: {enum_values}"
                )

            # Min/max validation for numbers
            if expected_type in {"number", "integer"}:
                minimum = field_def.get("minimum")
                maximum = field_def.get("maximum")
                if minimum is not None and value < minimum:
                    errors.append(
                        f"Input field '{field_name}' must be >= {minimum}"
                    )
                if maximum is not None and value > maximum:
                    errors.append(
                        f"Input field '{field_name}' must be <= {maximum}"
                    )

            # Min/max length for strings
            if expected_type == "string" and isinstance(value, str):
                min_length = field_def.get("minLength")
                max_length = field_def.get("maxLength")
                if min_length is not None and len(value) < min_length:
                    errors.append(
                        f"Input field '{field_name}' must be at least {min_length} characters"
                    )
                if max_length is not None and len(value) > max_length:
                    errors.append(
                        f"Input field '{field_name}' must be at most {max_length} characters"
                    )

        return errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate value against expected type.

        Args:
            value: Value to validate.
            expected_type: Expected type name.

        Returns:
            True if type matches.
        """
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected = type_mapping.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)

    def _substitute_inputs(
        self,
        data: Any,
        input_data: Dict[str, Any]
    ) -> Any:
        """
        Recursively substitute input placeholders in data.

        Supports placeholders like ${input.field_name}

        Args:
            data: Data structure to process.
            input_data: Input data for substitution.

        Returns:
            Data with substitutions applied.
        """
        if isinstance(data, str):
            # Replace ${input.field} placeholders
            import re
            pattern = r"\$\{input\.([^}]+)\}"

            def replace_match(match):
                field_name = match.group(1)
                value = input_data.get(field_name, match.group(0))
                return str(value) if not isinstance(value, str) else value

            # Check if entire string is a placeholder
            full_match = re.fullmatch(pattern, data)
            if full_match:
                field_name = full_match.group(1)
                return input_data.get(field_name, data)

            return re.sub(pattern, replace_match, data)

        elif isinstance(data, dict):
            return {
                key: self._substitute_inputs(value, input_data)
                for key, value in data.items()
            }

        elif isinstance(data, list):
            return [
                self._substitute_inputs(item, input_data)
                for item in data
            ]

        return data

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()

    def remove_from_cache(self, template_id: str) -> bool:
        """
        Remove a specific template from cache.

        Args:
            template_id: ID of template to remove.

        Returns:
            True if template was in cache.
        """
        if template_id in self._cache:
            del self._cache[template_id]
            return True
        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics.
        """
        return {
            "enabled": self.cache_enabled,
            "size": len(self._cache),
            "templates": list(self._cache.keys()),
            "total_size_bytes": sum(
                len(str(c.raw_content)) for c in self._cache.values()
            )
        }
