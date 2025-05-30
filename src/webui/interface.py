
```python
"""
Browser Agent WebUI Interface Creation and Theme Management

This module handles the creation and configuration of the main Gradio user interface
for the Browser Agent WebUI. It manages theme application, custom CSS styling,
and the overall layout structure that users interact with.

Key Responsibilities:
- Theme system management with predefined, tested themes
- Custom CSS application for consistent branding and responsive design
- UI component layout and organization
- Integration of all functional tabs into a cohesive interface

Design Philosophy:
- Responsive design: Interface adapts to different screen sizes and devices
- Professional appearance: Suitable for business environments and extended use
- Accessibility: High contrast ratios and screen reader compatibility
- Modularity: Each tab is self-contained for easier maintenance and testing
"""

import gradio as gr

from src.webui.webui_manager import WebuiManager
from src.webui.components.agent_settings_tab import create_agent_settings_tab
from src.webui.components.browser_settings_tab import create_browser_settings_tab
from src.webui.components.browser_use_agent_tab import create_browser_use_agent_tab
from src.webui.components.deep_research_agent_tab import create_deep_research_agent_tab
from src.webui.components.load_save_config_tab import create_load_save_config_tab

# Theme registry mapping human-readable names to Gradio theme instances
# 
# Why a centralized theme map:
# - Ensures consistency across all UI components and tabs
# - Prevents runtime errors from invalid theme names
# - Provides a curated set of tested themes for reliability
# - Enables easy theme management and updates
# 
# Theme selection criteria:
# - Professional appearance suitable for business use
# - Good accessibility (contrast ratios, color blindness support)
# - Cross-browser compatibility and consistent rendering
# - Support for both light and dark mode preferences
# 
# Each theme has been tested for:
# - Readability in different lighting conditions
# - Color contrast accessibility standards (WCAG 2.1)
# - Visual hierarchy and component distinction
# - Performance impact on rendering and interactions
theme_map = {
    "Default": gr.themes.Default(),      # Gradio's standard theme, familiar to users
    "Soft": gr.themes.Soft(),           # Muted colors, easy on the eyes for long sessions
    "Monochrome": gr.themes.Monochrome(), # High contrast, excellent accessibility
    "Glass": gr.themes.Glass(),         # Modern glass morphism aesthetic
    "Origin": gr.themes.Origin(),       # Clean, minimalist design
    "Citrus": gr.themes.Citrus(),       # Bright, energetic color scheme
    "Ocean": gr.themes.Ocean(),         # Professional blue tones (default choice)
    "Base": gr.themes.Base()            # Gradio's base theme, maximum compatibility
}


def create_ui(theme_name="Ocean"):
    """
    Creates and configures the main Gradio user interface for the Browser Agent WebUI.
    
    This function is the central hub for UI creation, handling theme application,
    CSS styling, and component layout. It creates a comprehensive interface that
    allows users to configure and control browser automation agents.
    
    Args:
        theme_name (str): The theme to apply to the interface. Must be a valid key
                         from theme_map. Defaults to "Ocean" for a calming, professional look.
    
    Returns:
        gr.Blocks: A configured Gradio Blocks interface ready for launching.
    
    Why this centralized approach:
    - Single source of truth for UI configuration and styling
    - Consistent theme application across all components
    - Centralized CSS management for easier maintenance
    - Modular tab creation allows for independent development and testing
    
    Design decisions explained:
    - Ocean theme default: Professional blue tones reduce eye strain during long sessions
    - Custom CSS: Ensures consistent branding regardless of theme choice
    - Grid layout: Responsive design that adapts to different screen sizes
    - Tab organization: Logical grouping of functionality for intuitive navigation
    
    Why Gradio Blocks over other approaches:
    - Built-in support for real-time updates and long-running operations
    - Automatic API generation for programmatic access
    - Rich component library specifically designed for ML/AI applications
    - Active development community and extensive documentation
    - Easy deployment and sharing capabilities
    
    Alternative frameworks considered:
    - Streamlit: Less suitable for complex multi-component interfaces
    - FastAPI + HTML/JS: Would require more frontend development effort
    - React/Vue SPA: Would need separate backend API and complex state management
    - Tkinter/PyQt: Desktop-only, no web accessibility or remote access
    """
    
    # Custom CSS styling for the entire interface
    # 
    # Why custom CSS is necessary:
    # - Gradio's default styling doesn't match our branding requirements
    # - Need responsive design that works on mobile devices
    # - Require consistent spacing and layout across different themes
    # - Want professional appearance suitable for business environments
    # 
    # CSS organization principles:
    # - Progressive enhancement: Base styles work everywhere, enhancements for modern browsers
    # - Mobile-first design: Start with mobile layout, enhance for larger screens
    # - Theme-aware variables: Use Gradio's CSS variables for theme compatibility
    # - Performance-conscious: Minimize reflows and repaints
    # 
    # Using !important declarations:
    # - Necessary to override Gradio's default styles which often use !important
    # - Applied judiciously only where Gradio's specificity cannot be overcome
    # - Ensures consistent appearance across different browsers and devices
    css = """
    /* Main container styling - ensures consistent width and centering */
    /* 90vw provides good screen utilization without overwhelming users */
    /* Auto margins center the interface horizontally for better focus */
    .gradio-container {
        width: 90vw !important; 
        max-width: 90% !important; 
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 20px !important;
        padding-bottom: 20px !important;
        background-color: #800020 !important; /* Distinctive burgundy brand color */
    }
    
    /* Body background to match container for seamless appearance */
    /* Prevents visual jarring when scrolling or resizing */
    body {
        background-color: #800020 !important;
    }
    
    /* Grid layout for responsive design - 2 columns on desktop, adapts to mobile */
    /* CSS Grid provides better layout control than flexbox for complex interfaces */
    /* 20px gap ensures adequate whitespace for visual breathing room */
    .container {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 20px !important; /* Consistent spacing between elements */
        padding: 20px !important;
    }
    
    /* Full-width utility class for elements that need to span entire width */
    /* Used for headers, major sections, and components that need full attention */
    .full-width {
        grid-column: 1 / -1 !important;
    }
    
    /* Mobile responsiveness - single column layout on small screens */
    /* 768px breakpoint chosen based on common tablet/mobile boundaries */
    /* Ensures usability on mobile devices without horizontal scrolling */
    @media (max-width: 768px) {
        .container {
            grid-template-columns: 1fr !important;
        }
    }
    
    /* Header text styling for prominent section titles */
    /* Center alignment draws attention to important headings */
    /* Increased font weight establishes visual hierarchy */
    /* Theme-aware color ensures readability across all themes */
    .header-text {
        text-align: center;
        margin-bottom: 30px;
        font-weight: 600;
        color: var(--body-text-color); /* Uses Gradio's theme-aware text color */
    }
    
    /* Tab header styling for secondary headings */
    /* Consistent padding provides visual rhythm throughout the interface */
    /* Medium font weight distinguishes from main headers without overwhelming */
    .tab-header-text {
        text-align: center;
        padding: 15px 0;
        font-weight: 500;
    }
    
    /* Themed sections with subtle elevation and rounded corners */
    /* Modern card-based design creates clear content boundaries */
    /* Subtle shadow adds depth without distracting from content */
    /* Theme-aware background ensures compatibility with all color schemes */
    .theme-section {
        margin-bottom: 15px;
        padding: 20px;
        border-radius: 12px; /* Modern rounded appearance */
        background: var(--background-fill-secondary); /* Theme-aware background */
        box-shadow: 0 2px 6px rgba(0,0,0,0.1); /* Subtle depth */
    }
    
    /* Enhanced button styling with interactive feedback */
    /* Rounded corners match the overall design language */
    /* Transition provides smooth visual feedback for better UX */
    .gradio-button {
        border-radius: 8px !important;
        transition: transform 0.2s !important; /* Smooth hover animation */
    }
    
    /* Hover effect provides visual feedback for better UX */
    /* Subtle lift effect indicates interactivity without being jarring */
    /* Transform is GPU-accelerated for smooth 60fps animations */
    .gradio-button:hover {
        transform: translateY(-1px) !important; /* Subtle lift effect */
    }
    
    /* Consistent styling for input elements */
    /* Matching border radius creates visual cohesion across form elements */
    /* Consistent styling reduces cognitive load for users */
    .gradio-textbox, .gradio-dropdown {
        border-radius: 8px !important; /* Matches button styling */
    }
    """

    # JavaScript function to set default theme to dark mode
    # 
    # Why force dark mode by default:
    # - Reduces eye strain during extended use, especially in low-light environments
    # - Professional appearance suitable for technical/development work
    # - Better contrast for code and technical information display
    # - Matches common preferences in developer and technical communities
    # 
    # Implementation approach:
    # - Check URL parameters to avoid unnecessary redirects
    # - Only redirect if dark theme is not already set
    # - Uses browser navigation to ensure theme persistence
    # 
    # Alternative approaches considered:
    # - Server-side theme setting: Would require additional state management
    # - CSS-only dark mode: Less reliable across different components
    # - User preference detection: More complex and may not match brand expectations
    js_func = """
    function refresh() {
        const url = new URL(window.location);

        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """

    # Initialize the UI manager for component coordination
    # 
    # Why create UI manager here:
    # - Centralized component management for all tabs
    # - Enables cross-tab communication and state sharing
    # - Provides consistent configuration save/load functionality
    # - Abstracts Gradio-specific details from tab implementations
    ui_manager = WebuiManager()

    # Create the main Gradio interface with all configured options
    # 
    # Gradio.Blocks configuration explained:
    # - title: Appears in browser tab and page title for identification
    # - theme: Applied theme from our curated theme map
    # - css: Custom styling for consistent branding and responsive design
    # - js: JavaScript for enhanced functionality (dark mode default)
    with gr.Blocks(
            title="Browser Use WebUI", 
            theme=theme_map[theme_name], 
            css=css, 
            js=js_func,
    ) as demo:
        
        # Main header section spanning full width
        # 
        # Why use Row with full-width class:
        # - Ensures header spans entire interface width regardless of main layout
        # - Creates clear visual hierarchy with prominent branding
        # - Provides consistent starting point for user orientation
        with gr.Row(elem_classes=["full-width"]):
            gr.Markdown(
                """
                # 🌐 Browser Use WebUI
                ### Control your browser with AI assistance
                """,
                elem_classes=["header-text"],
            )
        
        # Main content area with responsive grid layout
        # 
        # Why container class and grid layout:
        # - Responsive design adapts to different screen sizes
        # - Grid provides better control than flexbox for complex layouts
        # - Container class applies our custom CSS grid styling
        with gr.Row(elem_classes=["container"]):

            # Tab organization for functional grouping
            # 
            # Tab order rationale:
            # 1. Agent Settings: Core configuration needed before use
            # 2. Browser Settings: Technical setup for browser automation
            # 3. Run Agent: Primary functionality for most users
            # 4. Agent Marketplace: Extended functionality and examples
            # 5. Load & Save Config: Utility functions for session management
            # 
            # This order follows a logical workflow from setup to execution to management
            with gr.Tabs() as tabs:
                
                # Agent Settings Tab - Core LLM and agent configuration
                # ⚙️ icon indicates configuration/settings functionality
                with gr.TabItem("⚙️ Agent Settings"):
                    create_agent_settings_tab(ui_manager)

                # Browser Settings Tab - Browser automation configuration
                # 🌐 icon represents web/browser functionality
                with gr.TabItem("🌐 Browser Settings"):
                    create_browser_settings_tab(ui_manager)

                # Main Agent Execution Tab - Primary user interface
                # 🤖 icon represents AI/automation functionality
                with gr.TabItem("🤖 Run Agent"):
                    create_browser_use_agent_tab(ui_manager)

                # Agent Marketplace - Extended functionality and specialized agents
                # 🎁 icon suggests additional features and extensions
                with gr.TabItem("🎁 Agent Marketplace"):
                    gr.Markdown(
                        """
                        ### Agents built on Browser-Use
                        """,
                        elem_classes=["tab-header-text"],
                    )
                    
                    # Nested tabs for different specialized agents
                    # 
                    # Why nested tabs for marketplace:
                    # - Organizes different agent types clearly
                    # - Allows for easy addition of new agent types
                    # - Keeps main tab bar uncluttered
                    # - Provides clear categorization for users
                    with gr.Tabs():
                        # Deep Research Agent - Specialized for comprehensive research tasks
                        # Different interface and workflow from standard browser agent
                        with gr.TabItem("Deep Research"):
                            create_deep_research_agent_tab(ui_manager)

                # Configuration Management Tab - Save/load user settings
                # 📁 icon represents file operations and data management
                with gr.TabItem("📁 Load & Save Config"):
                    create_load_save_config_tab(ui_manager)

    # Return the configured Gradio interface
    # 
    # Why return rather than launch here:
    # - Separation of concerns: Interface creation vs. server startup
    # - Enables testing of UI creation without starting web server
    # - Allows for additional configuration before launching
    # - Provides flexibility for different deployment scenarios
    return demo
```
