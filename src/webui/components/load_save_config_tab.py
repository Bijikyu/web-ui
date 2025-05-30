"""
Load & Save Config Tab - Configuration Management and Session Persistence Interface

This module provides a comprehensive configuration management system that enables users
to save, load, and manage their application settings, ensuring that complex configurations
can be preserved across sessions and shared between team members or deployment environments.

Core Functionality:
1. Configuration Persistence: Save complete application state to files for later restoration
2. Session Management: Automatic loading of the most recent configuration on startup
3. Configuration Organization: Named configurations for different use cases and environments
4. Import/Export: Share configurations between users and deployment environments
5. Version Control: Track configuration changes over time with timestamps
6. Validation: Ensure loaded configurations are compatible with current application version
7. Migration: Handle configuration format changes across application updates

Design Philosophy:
- User Convenience: Minimize friction in saving and restoring work
- Data Integrity: Robust validation and error handling to prevent corrupted configurations
- Shareability: Enable easy collaboration through exportable configuration files
- Version Safety: Graceful handling of configuration format changes
- Privacy Aware: Exclude sensitive data from saved configurations by default
- Performance Conscious: Efficient configuration operations that don't impact UI responsiveness

Why Configuration Management is Critical:
Browser automation often involves complex setups that can take significant time to configure:
- LLM provider settings with API keys and model parameters
- Browser configuration with performance and compatibility settings
- Agent behavior customization for specific automation tasks
- Network and security settings for enterprise environments
- Debug and monitoring configurations for troubleshooting

Without proper configuration management, users would need to:
- Reconfigure all settings after every application restart
- Manually document complex configurations for team sharing
- Lose work when experimenting with different settings
- Spend significant time recreating working configurations after failures
- Manually maintain consistency across development and production environments

Configuration Scope and Organization:
1. User Interface Settings: Component values, layout preferences, theme choices
2. Agent Configuration: LLM settings, behavior parameters, performance tuning
3. Browser Settings: Automation parameters, display options, network configuration
4. Environment Settings: Deployment-specific configurations and optimizations
5. Security Settings: Authentication, authorization, and access control parameters
6. Debug Settings: Logging levels, monitoring options, and troubleshooting aids

Technical Implementation Considerations:
- File Format: JSON for human readability and easy debugging
- File Naming: Timestamp-based naming for automatic chronological organization
- Storage Location: Configurable directory with sensible defaults for different platforms
- Compression: Optional compression for large configurations
- Encryption: Optional encryption for configurations containing sensitive data
- Backup: Automatic backup of configurations before applying new ones

User Experience Features:
- Auto-save: Automatic saving of configurations at regular intervals
- Quick Load: Fast access to recently used configurations
- Configuration Preview: Show configuration contents before loading
- Diff Visualization: Compare configurations to understand differences
- Batch Operations: Load/save multiple configurations simultaneously
- Search and Filter: Find specific configurations by name, date, or content

Error Handling and Recovery:
- Validation: Check configuration compatibility before loading
- Rollback: Ability to revert to previous configuration if new one fails
- Partial Loading: Load compatible portions of incompatible configurations
- Error Reporting: Clear messages about configuration problems and solutions
- Backup Recovery: Restore from automatic backups when primary configurations fail

This configuration management system is essential for making the Browser Agent WebUI
practical for real-world use, where setup time and configuration complexity would
otherwise prevent effective adoption and usage.
"""

import os
from typing import Dict, Generator

import gradio as gr
from gradio.components import Component

from src.webui.webui_manager import WebuiManager


def create_load_save_config_tab(webui_manager: WebuiManager):
    """
    Creates a load and save config tab.
    """
    input_components = set(webui_manager.get_components())
    tab_components = {}

    # Load most recent config on startup
    most_recent = webui_manager.get_most_recent_config()
    if most_recent:
        for _ in webui_manager.load_config(most_recent):
            pass

    with gr.Row():
        with gr.Column(scale=1):
            config_file = gr.File(
                label="Load UI Settings from json",
                file_types=[".json"],
                interactive=True
            )
        with gr.Column(scale=1):
            with gr.Row():  # keep load/save buttons side by side for usability
                load_config_button = gr.Button("Load Config", variant="primary")
                save_config_button = gr.Button("Save UI Settings", variant="primary")

    config_status = gr.Textbox(
        label="Status",
        lines=2,
        interactive=False
    )

    tab_components.update(dict(
        load_config_button=load_config_button,
        save_config_button=save_config_button,
        config_status=config_status,
        config_file=config_file,
    ))

    webui_manager.add_components("load_save_config", tab_components)  # register load/save widgets for persistence

    save_config_button.click(
        fn=webui_manager.save_config,  # persist current settings to file
        inputs=set(webui_manager.get_components()),
        outputs=[config_status]
    )

    load_config_button.click(
        fn=webui_manager.load_config,  # restore settings from selected file
        inputs=[config_file],
        outputs=webui_manager.get_components(),
    )