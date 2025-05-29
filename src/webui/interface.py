import gradio as gr

from src.webui.webui_manager import WebuiManager
from src.webui.components.agent_settings_tab import create_agent_settings_tab
from src.webui.components.browser_settings_tab import create_browser_settings_tab
from src.webui.components.browser_use_agent_tab import create_browser_use_agent_tab
from src.webui.components.deep_research_agent_tab import create_deep_research_agent_tab
from src.webui.components.load_save_config_tab import create_load_save_config_tab

theme_map = {
    "Default": gr.themes.Default(),
    "Soft": gr.themes.Soft(),
    "Monochrome": gr.themes.Monochrome(),
    "Glass": gr.themes.Glass(),
    "Origin": gr.themes.Origin(),
    "Citrus": gr.themes.Citrus(),
    "Ocean": gr.themes.Ocean(),
    "Base": gr.themes.Base()
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
    
    Why this approach:
    - Custom CSS ensures consistent branding and responsive design
    - Modular component creation allows for easier maintenance and testing
    - Theme system provides visual customization while maintaining usability
    - Grid layout adapts to different screen sizes for accessibility
    
    Design decisions:
    - 90vw width provides good use of screen real estate without overwhelming users
    - Burgundy background (#800020) creates a distinctive, professional appearance
    - Grid layout with 2 columns on desktop, 1 on mobile ensures responsive design
    - Rounded corners and subtle shadows create modern, polished appearance
    """
    
    # Custom CSS styling for the entire interface
    # Using !important to override Gradio's default styles where necessary
    # This ensures consistent branding and layout across different browsers and devices
    css = """
    /* Main container styling - ensures consistent width and centering */
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
    body {
        background-color: #800020 !important;
    }
    
    /* Grid layout for responsive design - 2 columns on desktop, adapts to mobile */
    .container {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 20px !important; /* Consistent spacing between elements */
        padding: 20px !important;
    }
    
    /* Full-width utility class for elements that need to span entire width */
    .full-width {
        grid-column: 1 / -1 !important;
    }
    
    /* Mobile responsiveness - single column layout on small screens */
    @media (max-width: 768px) {
        .container {
            grid-template-columns: 1fr !important;
        }
    }
    
    /* Header text styling for prominent section titles */
    .header-text {
        text-align: center;
        margin-bottom: 30px;
        font-weight: 600;
        color: var(--body-text-color); /* Uses Gradio's theme-aware text color */
    }
    
    /* Tab header styling for secondary headings */
    .tab-header-text {
        text-align: center;
        padding: 15px 0;
        font-weight: 500;
    }
    
    /* Themed sections with subtle elevation and rounded corners */
    .theme-section {
        margin-bottom: 15px;
        padding: 20px;
        border-radius: 12px; /* Modern rounded appearance */
        background: var(--background-fill-secondary); /* Theme-aware background */
        box-shadow: 0 2px 6px rgba(0,0,0,0.1); /* Subtle depth */
    }
    
    /* Enhanced button styling with interactive feedback */
    .gradio-button {
        border-radius: 8px !important;
        transition: transform 0.2s !important; /* Smooth hover animation */
    }
    
    /* Hover effect provides visual feedback for better UX */
    .gradio-button:hover {
        transform: translateY(-1px) !important; /* Subtle lift effect */
    }
    
    /* Consistent styling for input elements */
    .gradio-textbox, .gradio-dropdown {
        border-radius: 8px !important; /* Matches button styling */
    }
    """

    # dark mode in default
    js_func = """
    function refresh() {
        const url = new URL(window.location);

        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """

    ui_manager = WebuiManager()

    with gr.Blocks(
            title="Browser Use WebUI", theme=theme_map[theme_name], css=css, js=js_func,
    ) as demo:
        with gr.Row(elem_classes=["full-width"]):
            gr.Markdown(
                """
                # 🌐 Browser Use WebUI
                ### Control your browser with AI assistance
                """,
                elem_classes=["header-text"],
            )
        with gr.Row(elem_classes=["container"]):

            with gr.Tabs() as tabs:
                with gr.TabItem("⚙️ Agent Settings"):
                    create_agent_settings_tab(ui_manager)

                with gr.TabItem("🌐 Browser Settings"):
                    create_browser_settings_tab(ui_manager)

                with gr.TabItem("🤖 Run Agent"):
                    create_browser_use_agent_tab(ui_manager)

                with gr.TabItem("🎁 Agent Marketplace"):
                    gr.Markdown(
                        """
                        ### Agents built on Browser-Use
                        """,
                        elem_classes=["tab-header-text"],
                    )
                    with gr.Tabs():
                        with gr.TabItem("Deep Research"):
                            create_deep_research_agent_tab(ui_manager)

                with gr.TabItem("📁 Load & Save Config"):
                    create_load_save_config_tab(ui_manager)

    return demo
