# Load environment variables from .env file before any other imports
# This ensures API keys and configuration are available throughout the application
from dotenv import load_dotenv
load_dotenv()

import argparse
from src.webui.interface import theme_map, create_ui


def main():
    """
    Main entry point for the Browser Agent WebUI application.
    
    This function sets up command-line argument parsing and launches the Gradio interface.
    The WebUI provides a user-friendly interface for interacting with browser automation
    agents that can perform tasks like web scraping, form filling, and general web navigation.
    
    Why this approach:
    - Uses argparse for flexibility in deployment scenarios (different IPs/ports)
    - Defaults to localhost (127.0.0.1) for security but allows 0.0.0.0 for public access
    - Port 7788 is chosen to avoid conflicts with common services
    - Theme selection allows user customization while maintaining consistency
    
    The queue() call enables handling multiple concurrent users, which is essential
    for a web-based tool that may have multiple simultaneous sessions.
    """
    parser = argparse.ArgumentParser(description="Gradio WebUI for Browser Agent")
    
    # IP binding: defaults to localhost for security, but can be changed for public access
    # Using 0.0.0.0 makes the service accessible from external networks
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    
    # Port selection: 7788 avoids common port conflicts while being memorable
    # In production environments, this may be proxied through standard HTTP ports
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on")
    
    # Theme system: provides visual customization while ensuring all themes are validated
    # Choices are restricted to prevent invalid theme names that could break the UI
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    
    args = parser.parse_args()

    # Create the Gradio interface with the selected theme
    # The theme is applied during UI creation to ensure consistent styling
    demo = create_ui(theme_name=args.theme)
    
    # Enable queuing for concurrent user handling and launch the server
    # queue() is essential for handling multiple users and long-running operations
    # launch() with server_name and server_port allows flexible deployment options
    demo.queue().launch(server_name=args.ip, server_port=args.port)


if __name__ == '__main__':
    """
    Entry point guard ensures this code only runs when the script is executed directly,
    not when imported as a module. This is important for clean module imports and testing.
    """
    main()
