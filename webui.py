
"""
Browser Agent WebUI - Main Entry Point

This module serves as the primary launcher for the Browser Agent WebUI application,
providing a command-line interface to configure and start the Gradio-based web interface.

The Browser Agent WebUI is a user-friendly interface that allows users to interact with
browser automation agents for tasks like web scraping, form filling, and general web navigation.

Design Philosophy:
- Separation of concerns: This launcher handles only CLI parsing and server startup
- Flexibility first: Command-line arguments allow adaptation to different deployment scenarios
- Security by default: Defaults to localhost binding but allows override for public access
- Port conflict avoidance: Uses non-standard port 7788 to minimize service conflicts
"""

# Load environment variables from .env file before any other imports
# This ensures API keys and configuration are available throughout the application
#
# Why this is first: Environment variables (like API keys, database URLs, etc.) are often
# required during module imports. Loading them first prevents ImportError or runtime
# failures when other modules try to access configuration during their initialization.
# The dotenv approach allows for local development flexibility while supporting
# production environment variable injection.
from dotenv import load_dotenv
load_dotenv()

import argparse
from src.webui.interface import theme_map, create_ui


def main():
    """
    Main entry point for the Browser Agent WebUI application.
    
    This function orchestrates the complete startup sequence:
    1. Parses command-line arguments for deployment flexibility
    2. Creates the Gradio interface with user-specified theme
    3. Launches the web server with specified network binding
    
    Design Rationale:
    The WebUI provides a user-friendly interface for interacting with browser automation
    agents that can perform complex web tasks. This design separates the web interface
    from the core agent logic, allowing for:
    - Easy deployment in different environments (local dev, staging, production)
    - Multiple concurrent users through Gradio's built-in queue system
    - Theme customization for better user experience
    - Network configuration flexibility for security vs. accessibility tradeoffs
    
    Why Gradio was chosen:
    - Built-in support for concurrent users and long-running operations
    - Automatic API generation for programmatic access
    - Rich UI components suitable for AI/ML applications
    - Easy deployment and sharing capabilities
    - Active development and community support
    
    Why this approach over alternatives:
    - FastAPI/Flask: Would require more boilerplate for UI components and real-time updates
    - Streamlit: Less suitable for complex multi-component interfaces and concurrent users
    - React/Vue SPA: Would require separate backend API and more complex deployment
    
    The queue() call is essential because browser automation tasks can be long-running
    (30+ seconds), and without queuing, the interface would block for other users.
    """
    parser = argparse.ArgumentParser(description="Gradio WebUI for Browser Agent")
    
    # IP binding configuration: Security vs. Accessibility tradeoff
    # 
    # Default: 127.0.0.1 (localhost only) for security in development
    # Override: 0.0.0.0 for production deployment where external access is needed
    #
    # Why this matters:
    # - 127.0.0.1: Only accessible from the same machine, prevents accidental exposure
    # - 0.0.0.0: Binds to all network interfaces, allows external connections
    # - In Docker/cloud environments, 0.0.0.0 is often required for proper routing
    # - Security consideration: External binding should be paired with proper authentication
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    
    # Port selection: Avoiding conflicts while maintaining memorability
    # 
    # 7788 chosen specifically because:
    # - Above 1024: Doesn't require root privileges on Unix systems
    # - Not in common service range (3000-8080): Reduces conflict with other dev tools
    # - Memorable pattern: Easy to remember and type
    # - Not a reserved port: Won't conflict with system services
    #
    # In production environments, this is typically proxied through standard HTTP ports
    # (80/443) via nginx, Apache, or cloud load balancers. The application doesn't
    # handle HTTPS directly to follow the principle of separation of concerns.
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on")
    
    # Theme system: Balancing customization with consistency
    #
    # Why restrict choices to theme_map.keys():
    # - Prevents runtime errors from invalid theme names that could crash the UI
    # - Ensures all themes are tested and validated before deployment
    # - Provides a curated experience rather than unlimited customization
    # - Makes it easier to maintain visual consistency across deployments
    #
    # The theme system allows visual customization while ensuring all themes:
    # - Meet accessibility standards (contrast ratios, color blindness considerations)
    # - Work consistently across all UI components
    # - Are tested with different screen sizes and browsers
    #
    # "Ocean" default chosen for:
    # - Professional appearance suitable for business environments
    # - Good contrast ratios for accessibility
    # - Calming blue tones that reduce eye strain during long sessions
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    
    # Parse all command-line arguments
    # This happens after all arguments are defined to catch any parsing errors early
    # and provide helpful error messages to users who provide invalid arguments
    args = parser.parse_args()

    # Create the Gradio interface with the selected theme
    # 
    # Why create_ui is a separate function:
    # - Separation of concerns: UI creation logic is isolated from startup logic
    # - Testability: The UI can be created and tested without starting a server
    # - Reusability: The same UI creation logic could be used in different contexts
    # - Configuration flexibility: Theme is applied during creation for consistency
    #
    # The theme is applied during UI creation rather than after because:
    # - Ensures all components are styled consistently from initialization
    # - Prevents brief moments of default styling before theme application
    # - Allows theme-specific component configurations if needed
    demo = create_ui(theme_name=args.theme)
    
    # Enable queuing for concurrent user handling and launch the server
    #
    # Why queue() is essential:
    # - Browser automation tasks are inherently long-running (can take 30+ seconds)
    # - Without queuing, the entire interface would freeze for all users during task execution
    # - Gradio's queue system handles this by running tasks in background workers
    # - Allows multiple users to submit tasks simultaneously
    # - Provides progress updates and cancellation capabilities
    #
    # Why launch() with these specific parameters:
    # - server_name=args.ip: Allows flexible network binding based on deployment needs
    # - server_port=args.port: Enables port customization for different environments
    # - No share=True: Avoids creating public tunnels which could be security risks
    # - No auth: Authentication is handled at the infrastructure level (proxy, VPN, etc.)
    #
    # Alternative considered: Using gunicorn/uvicorn for production deployment
    # Decision: Gradio's built-in server is sufficient for most use cases and simpler to configure
    # For high-scale production, this could be wrapped in a proper WSGI/ASGI server
    demo.queue().launch(server_name=args.ip, server_port=args.port)


if __name__ == '__main__':
    """
    Entry point guard: Ensures main() only runs when script is executed directly.
    
    Why this pattern is important:
    - Prevents main() from running when this module is imported by other scripts
    - Essential for clean module imports during testing
    - Allows the module to be imported for its functions without side effects
    - Standard Python practice for executable scripts
    
    This becomes critical when:
    - Running unit tests that import this module
    - Using this module as part of a larger application
    - Implementing integration tests that need to control startup timing
    - Building documentation that imports modules for introspection
    
    Without this guard, importing this module would immediately start the web server,
    which would cause issues in testing environments and make the module unusable
    as a library component.
    """
    main()
