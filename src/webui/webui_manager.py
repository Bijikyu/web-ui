
"""
WebUI Manager - Central State and Component Management

This module provides the core management system for the Browser Agent WebUI,
handling component registration, state persistence, and coordination between
different UI tabs and their associated functionality.

Design Philosophy:
- Centralized state management: Single source of truth for all UI component states
- Component abstraction: Hide Gradio-specific details behind a clean interface
- Persistence layer: Automatic saving/loading of user configurations
- Type safety: Strong typing for component management and state handling

The WebuiManager serves as the backbone of the entire WebUI system, providing:
- Component registration and lookup by human-readable IDs
- Configuration save/load functionality for user convenience
- State management for long-running agent processes
- Coordination between multiple agent types (Browser Use, Deep Research)
"""

import json
from collections.abc import Generator
from typing import TYPE_CHECKING
import os
import gradio as gr
from datetime import datetime

from typing import Optional, Dict, List, Any  # Import type hints for component value return types
# Removed unused uuid import as it's not used in this module

import asyncio

from gradio.components import Component
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.agent.service import Agent
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContext
from src.controller.custom_controller import CustomController
from src.agent.deep_research.deep_research_agent import DeepResearchAgent
from src.utils.utils import ensure_dir  # Utility function to guarantee directory existence


class WebuiManager:
    """
    Central management system for the Browser Agent WebUI application.
    
    This class serves as the coordination hub for all UI components, agent instances,
    and persistent configuration. It abstracts away Gradio-specific implementation
    details and provides a clean interface for component management.
    
    Key Responsibilities:
    1. Component Registration: Maps human-readable IDs to Gradio components
    2. State Management: Maintains agent states and execution contexts
    3. Configuration Persistence: Handles saving/loading of user settings
    4. Agent Coordination: Manages multiple concurrent agent instances
    
    Design Rationale:
    - Bidirectional mapping (ID->Component and Component->ID) enables flexible access
    - Separate initialization methods for different agent types prevent state conflicts
    - Configuration auto-save prevents user frustration from lost settings
    - Directory management ensures file operations never fail due to missing paths
    
    Why this architecture over alternatives:
    - Global state: Would create testing difficulties and coupling issues
    - Component-local state: Would prevent cross-tab coordination and persistence
    - Database storage: Overkill for local configuration, adds deployment complexity
    """
    
    def __init__(self, settings_save_dir: str = "./tmp/webui_settings"):
        """
        Initialize the WebUI manager with component tracking and configuration storage.
        
        Args:
            settings_save_dir (str): Directory path for storing user configuration files.
                                   Defaults to "./tmp/webui_settings" for development convenience.
        
        Design decisions:
        - Bidirectional component mapping enables both ID-based and component-based lookups
        - Default directory in tmp/ keeps configurations separate from source code
        - Directory creation on init prevents runtime failures during save operations
        
        The bidirectional mapping is essential because:
        - ID-based lookup: Needed when updating specific components from business logic
        - Component-based lookup: Required when processing Gradio event data
        - This approach eliminates the need for linear searches or duplicate storage
        """
        # Bidirectional component mapping for flexible access patterns
        # This enables both ID->Component and Component->ID lookups efficiently
        self.id_to_component: dict[str, Component] = {}
        self.component_to_id: dict[Component, str] = {}

        # Configuration persistence setup
        # Ensures user settings survive application restarts
        self.settings_save_dir = settings_save_dir
        ensure_dir(self.settings_save_dir)  # Guarantee directory exists to prevent save failures

    def init_browser_use_agent(self) -> None:
        """
        Initialize state containers for Browser Use Agent functionality.
        
        This method sets up all necessary state variables for managing a Browser Use
        Agent instance, including browser resources, execution state, and user interaction.
        
        Why separate initialization methods:
        - Different agent types have different state requirements
        - Prevents state pollution between agent types
        - Enables clean state reset without affecting other agents
        - Allows for type-specific optimization and resource management
        
        State variables explained:
        - bu_agent: The core Browser Use Agent instance for task execution
        - bu_browser/bu_browser_context: Browser automation resources requiring cleanup
        - bu_controller: Interface layer between agent and UI for user interactions
        - bu_chat_history: Conversation log for maintaining context across interactions
        - bu_response_event: Synchronization primitive for handling user input requests
        - bu_user_help_response: Storage for user responses to agent questions
        - bu_current_task: AsyncIO task handle for cancellation and monitoring
        - bu_agent_task_id: Unique identifier for correlating UI events with agent actions
        
        All initialized as None/empty to ensure clean state and prevent stale references.
        """
        # Core agent instance - the main execution engine
        self.bu_agent: Optional[Agent] = None
        
        # Browser automation resources - require careful lifecycle management
        # These must be properly closed to prevent resource leaks
        self.bu_browser: Optional[CustomBrowser] = None
        self.bu_browser_context: Optional[CustomBrowserContext] = None
        
        # Controller provides the interface between agent and UI
        # Handles user input requests and response coordination
        self.bu_controller: Optional[CustomController] = None
        
        # Chat history maintains conversation context for better user experience
        # Formatted as list of message dictionaries for Gradio chatbot component
        self.bu_chat_history: List[Dict[str, Optional[str]]] = []
        
        # Synchronization primitives for handling asynchronous user interactions
        # Agent may need to pause execution and wait for user input
        self.bu_response_event: Optional[asyncio.Event] = None
        self.bu_user_help_response: Optional[str] = None
        
        # Task management for execution control
        # Enables stopping, monitoring, and cleanup of running agents
        self.bu_current_task: Optional[asyncio.Task] = None
        self.bu_agent_task_id: Optional[str] = None

    def init_deep_research_agent(self) -> None:
        """
        Initialize state containers for Deep Research Agent functionality.
        
        This method sets up the necessary state variables for managing Deep Research
        Agent instances, which have different requirements than Browser Use Agents.
        
        Why Deep Research Agent needs separate initialization:
        - Different execution model (workflow-based vs. interactive)
        - Different resource requirements (multiple browser instances)
        - Different output patterns (research reports vs. direct browser actions)
        - Different user interaction patterns (less real-time, more batch-oriented)
        
        State variables explained:
        - dr_agent: The Deep Research Agent instance managing the research workflow
        - dr_current_task: Task handle for the research process (typically longer-running)
        - dr_task_id: Unique identifier for research sessions  # // rename to match tab references
        - dr_save_dir: Directory for storing research outputs (reports, intermediate data)
        
        The Deep Research Agent operates differently from Browser Use Agent:
        - Longer execution times (minutes to hours vs. seconds to minutes)
        - Multiple output files (reports, plans, search results)
        - Less interactive (fewer user input requests during execution)
        - More resource-intensive (multiple browser instances for parallel research)
        """
        # Core research agent instance
        self.dr_agent: Optional[DeepResearchAgent] = None
        
        # Task management for research workflow execution
        # Research tasks are typically long-running and less interactive
        self.dr_current_task = None
        self.dr_task_id: Optional[str] = None  # // store active research task ID
        
        # Output directory for research artifacts
        # Research generates multiple files: reports, plans, search results, etc.
        self.dr_save_dir: Optional[str] = None

    def add_components(self, tab_name: str, components_dict: dict[str, "Component"]) -> None:
        """
        Register UI components with the manager for later access and management.
        
        This method establishes the mapping between human-readable component IDs
        and Gradio component instances, enabling clean separation between UI
        structure and business logic.
        
        Args:
            tab_name (str): Namespace prefix for component IDs, typically the tab name.
                          This prevents naming conflicts between tabs.
            components_dict (dict): Mapping of component names to Gradio component instances.
        
        ID format: "{tab_name}.{component_name}"
        
        Why this approach:
        - Namespacing prevents component ID conflicts between tabs
        - Hierarchical naming makes component relationships clear
        - Bidirectional mapping enables efficient lookups in both directions
        - Explicit registration makes component dependencies visible
        
        Example usage:
        ```python
        components = {
            "submit_button": gr.Button("Submit"),
            "status_text": gr.Textbox("Ready")
        }
        manager.add_components("agent_tab", components)
        # Creates IDs: "agent_tab.submit_button", "agent_tab.status_text"
        ```
        
        Alternative approaches considered:
        - Automatic discovery: Would create implicit dependencies and fragile coupling
        - Global namespace: Would cause naming conflicts and maintenance issues
        - Component-only storage: Would require linear searches for reverse lookups
        """
        for comp_name, component in components_dict.items():
            # Create hierarchical ID with tab namespace to prevent conflicts
            comp_id = f"{tab_name}.{comp_name}"
            
            # Establish bidirectional mapping for efficient access
            self.id_to_component[comp_id] = component  # map ID to component for later lookup
            self.component_to_id[component] = comp_id  # reverse map for event handling

    def get_components(self) -> list["Component"]:
        """
        Retrieve all registered Gradio components.
        
        Returns:
            list[Component]: List of all registered Gradio component instances.
        
        Use cases:
        - Bulk operations on all components (configuration save/load)
        - Global event handler registration
        - Debugging and introspection
        - Component validation and health checks
        
        Why return a list rather than the dictionary:
        - Simpler iteration for common use cases
        - Hides internal storage structure for better encapsulation
        - Prevents accidental modification of the internal mapping
        """
        return list(self.id_to_component.values())

    def get_component_by_id(self, comp_id: str) -> "Component":
        """
        Retrieve a specific component by its hierarchical ID.
        
        Args:
            comp_id (str): Hierarchical component ID in format "tab_name.component_name"
        
        Returns:
            Component: The requested Gradio component instance
        
        Raises:
            KeyError: If the component ID is not found (fails fast for debugging)
        
        Why fail fast with KeyError:
        - Makes programming errors immediately visible during development
        - Prevents silent failures that could lead to confusing UI behavior
        - Encourages proper error handling in calling code
        - Standard Python dictionary behavior that developers expect
        
        Usage patterns:
        - Updating specific UI elements from business logic
        - Setting up event handlers for particular components
        - Accessing component state during configuration operations
        """
        return self.id_to_component[comp_id]

    def get_id_by_component(self, comp: "Component") -> str:
        """
        Retrieve the hierarchical ID for a given component instance.
        
        Args:
            comp (Component): Gradio component instance
        
        Returns:
            str: Hierarchical component ID in format "tab_name.component_name"
        
        Raises:
            KeyError: If the component is not registered
        
        Use cases:
        - Processing Gradio event data that provides component instances
        - Logging and debugging component interactions
        - Dynamic component discovery and introspection
        - Building component relationship maps
        
        Why this reverse lookup is necessary:
        - Gradio event handlers receive component instances, not IDs
        - Business logic often needs to identify which component triggered an event
        - Configuration save/load needs to map component instances back to storage keys
        """
        return self.component_to_id[comp]

    def get_component_value(self, components: Dict[Component, Any], tab: str, key: str, default: Any = None) -> Any:
        """
        Extract component value from Gradio's component state dictionary using hierarchical ID.
        
        This method provides a clean interface for accessing component values from
        Gradio's event system, which passes component states as a dictionary mapping
        component instances to their current values.
        
        Args:
            components (Dict[Component, Any]): Gradio's component state dictionary from events
            tab (str): Tab namespace for the component
            key (str): Component name within the tab
            default (Any): Default value if component not found or has no value
        
        Returns:
            Any: The current value of the specified component, or default if not found
        
        Why this abstraction is valuable:
        - Hides the complexity of Gradio's component->value mapping
        - Provides consistent error handling with sensible defaults
        - Enables clean separation between UI event handling and business logic
        - Reduces boilerplate code in event handlers
        
        Design rationale for default values:
        - Graceful degradation when components are missing or not yet initialized
        - Prevents crashes during partial UI updates or configuration loading
        - Enables optional components that don't break functionality when absent
        - Simplifies testing by eliminating need to mock every component
        
        Example usage:
        ```python
        def handle_submit(components):
            task = manager.get_component_value(components, "agent_tab", "task_input", "")
            if not task:
                return  # Gracefully handle empty input
            # Process task...
        ```
        """
        # Construct hierarchical ID from tab and component name
        comp_id = f"{tab}.{key}"
        
        # Look up component instance using our ID mapping
        component = self.id_to_component.get(comp_id)
        
        # Return component value if found, otherwise return default
        # This two-step process handles both missing components and missing values gracefully
        return components.get(component, default) if component else default
        
    def get_most_recent_config(self) -> Optional[str]:
        """
        Find the most recently modified configuration file for auto-loading.
        
        This method implements a "resume last session" feature by identifying
        the configuration file with the most recent modification time.
        
        Returns:
            Optional[str]: Full path to the most recent config file, or None if none exist
        
        Why this functionality improves user experience:
        - Reduces friction when restarting the application
        - Prevents loss of work when users forget to manually save configurations
        - Enables quick iteration during development and testing
        - Provides a natural "restore session" capability
        
        Implementation details:
        - Only considers .json files to avoid processing non-configuration files
        - Uses file modification time as the sorting criterion
        - Returns None rather than raising exceptions for missing directories/files
        - Handles edge cases gracefully (empty directory, no JSON files)
        
        Alternative approaches considered:
        - Explicit session management: More complex, requires additional UI
        - Database storage: Overkill for local configuration files
        - Timestamp in filename: Already implemented in save_config method
        - Last-accessed tracking: Would require additional metadata storage
        """
        # Check if configuration directory exists before attempting to read it
        if not os.path.exists(self.settings_save_dir):
            return None
            
        # Find all JSON configuration files in the settings directory
        config_files = [os.path.join(self.settings_save_dir, f) 
                       for f in os.listdir(self.settings_save_dir) 
                       if f.endswith('.json')]
        
        # Return None if no configuration files found
        if not config_files:
            return None
            
        # Return the file with the most recent modification time
        # max() with key=os.path.getmtime finds the file with the latest timestamp
        return max(config_files, key=os.path.getmtime)

    def save_config(self, components: Dict["Component", str]) -> None:
        """
        Persist current UI component states to a timestamped configuration file.
        
        This method captures the current state of all interactive UI components
        and saves them in a JSON format for later restoration, providing users
        with session persistence and configuration management.
        
        Args:
            components (Dict[Component, str]): Gradio's component state dictionary
                                             mapping component instances to their values
        
        Returns:
            str: Full path to the saved configuration file
        
        Why selective component saving:
        - Buttons: Don't have meaningful state to save (they represent actions, not data)
        - File components: File paths may not be valid across sessions or machines
        - Non-interactive components: Display-only components don't need persistence
        - This approach saves only user-input data that should be restored
        
        Filename format: "YYYYMMDD-HHMMSS.json"
        - Timestamp-based naming ensures unique filenames and natural ordering
        - ISO-like format is both human-readable and machine-sortable
        - JSON extension makes file type clear and enables syntax highlighting
        
        Component filtering logic:
        - Exclude buttons: isinstance() check for gr.Button plus string-based fallback
        - Exclude files: isinstance() check for gr.File plus string-based fallback
        - Exclude non-interactive: Check interactive property to avoid read-only components
        - String-based fallbacks handle edge cases where isinstance() might fail
        
        Design decisions:
        - JSON format: Human-readable, widely supported, easy to debug
        - Indented output: Improves readability for debugging and manual editing
        - Error handling: File I/O errors are allowed to propagate for debugging
        - Directory guarantee: ensure_dir() in __init__ prevents save failures
        """
        # Dictionary to store component states that should be persisted
        cur_settings = {}  # store user-provided values for JSON persistence
        
        for comp in components:
            # Filter out components that shouldn't be saved
            
            # Skip buttons - they represent actions, not persistent state
            is_button = isinstance(comp, gr.Button) or comp.__class__.__name__ == "DummyButton"
            
            # Skip file components - file paths may not be valid across sessions
            is_file = isinstance(comp, gr.File) or comp.__class__.__name__ == "DummyFile"
            
            # Only save interactive components that have meaningful persistent state
            if not is_button and not is_file and str(getattr(comp, "interactive", True)).lower() != "false":
                # Get component ID and store its current value
                comp_id = self.get_id_by_component(comp)
                cur_settings[comp_id] = components[comp]

        # Generate timestamp-based filename for unique identification
        config_name = datetime.now().strftime("%Y%m%d-%H%M%S")
        config_path = os.path.join(self.settings_save_dir, f"{config_name}.json")
        
        # Save configuration with pretty-printing for readability
        with open(config_path, "w") as fw:
            json.dump(cur_settings, fw, indent=4)

        # Return the path for caller feedback and logging
        return config_path

    def load_config(self, config_path: str):
        """
        Restore UI component states from a saved configuration file.
        
        This method reads a previously saved configuration and generates the
        appropriate Gradio component updates to restore the UI to its saved state.
        
        Args:
            config_path (str): Full path to the configuration file to load
        
        Yields:
            Dict[Component, Component]: Gradio component updates to apply to the UI
        
        Why this is a generator:
        - Gradio requires component updates to be returned from event handlers
        - Generator pattern allows for streaming updates if needed in the future
        - Consistent with Gradio's event handling patterns
        - Enables potential progress reporting during large configuration loads
        
        Component recreation strategy:
        - Create new component instances with loaded values rather than modifying existing ones
        - Ensures clean state and triggers proper Gradio update mechanisms
        - Handles special cases like Chatbot components that need type specification
        - Preserves component properties while updating values
        
        Special handling for Chatbot components:
        - Chatbot components require type="messages" parameter for proper display
        - This handles the conversation history format expected by Gradio
        - Other components use their default constructors with new values
        
        Error handling approach:
        - File I/O errors are allowed to propagate for debugging visibility
        - Missing components are silently skipped to handle partial configurations
        - Invalid JSON will raise exceptions for immediate feedback
        
        Status reporting:
        - Updates a dedicated status component to provide user feedback
        - Success message includes the loaded configuration path for transparency
        - Helps users understand which configuration was applied
        """
        # Load configuration data from JSON file
        with open(config_path, "r") as fr:
            ui_settings = json.load(fr)

        # Dictionary to accumulate component updates for Gradio
        update_components = {}  # collect per-component updates to return to Gradio
        
        # Process each saved component setting
        for comp_id, comp_val in ui_settings.items():
            if comp_id in self.id_to_component:
                comp = self.id_to_component[comp_id]
                
                # Special handling for Chatbot components
                # Chatbot requires type="messages" for proper conversation display
                if comp.__class__.__name__ == "Chatbot":
                    update_components[comp] = comp.__class__(value=comp_val, type="messages")
                else:
                    # Standard component update with new value
                    update_components[comp] = comp.__class__(value=comp_val)

        # Update status component to confirm successful loading
        config_status = self.id_to_component["load_save_config.config_status"]
        update_components.update(
            {
                config_status: config_status.__class__(value=f"Successfully loaded config: {config_path}")
            }
        )
        
        # Yield the component updates for Gradio to apply
        yield update_components
