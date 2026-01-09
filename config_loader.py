"""
Configuration loader for MCP servers using OmegaConf.
Loads server configuration from YAML files.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from omegaconf import OmegaConf


def load_server_config(server_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a specific MCP server from YAML file.

    Args:
        server_name: Name of the server (e.g., "math", "code_lint")
        config_path: Path to the YAML config file. If None, uses default path.

    Returns:
        Dictionary containing server-specific configuration with validated transport.
        Note: stdio transport doesn't require host/port.
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = Path(config_path)

    # Default configuration (stdio doesn't need host/port)
    defaults = {
        "math": {"port": 8000},
        "code_lint": {"port": 8001},
    }
    default_port = defaults.get(server_name, {}).get("port", 8000)

    default_config = {
        "transport": "stdio",
        "host": "0.0.0.0",
        "port": default_port,
    }

    if not config_path.exists():
        return {"transport": "stdio"}

    try:
        # Load config using OmegaConf
        cfg = OmegaConf.load(config_path)

        # Get server-specific config or use root-level config
        if server_name in cfg:
            server_cfg = cfg[server_name]
        else:
            server_cfg = cfg

        # Merge with defaults
        config = OmegaConf.merge(OmegaConf.create(default_config), server_cfg)

        # Validate transport (must be one of: stdio, http, sse, streamable-http)
        valid_transports = {"stdio", "http", "sse", "streamable-http"}
        transport = config.get("transport", "stdio")
        if transport not in valid_transports:
            print(f"Warning: Invalid transport '{transport}', using 'stdio'")
            transport = "stdio"

        # stdio doesn't need host/port
        if transport == "stdio":
            return {"transport": "stdio"}

        # Other transports need host and port
        return {
            "transport": transport,
            "host": config.get("host", "0.0.0.0"),
            "port": config.get("port", default_port),
        }
    except Exception as e:
        print(f"Warning: Failed to load config for {server_name} from {config_path}: {e}")
        print("Using default configuration")
        return {"transport": "stdio"}
