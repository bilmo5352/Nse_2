"""
Utility functions for browser management in headless environments.
Handles xvfb setup for headed mode on servers without display.
"""

import os
import platform


def get_browser_launch_args(headless: bool):
    """
    Get browser launch arguments, handling headed mode in headless environments.
    
    The startup script (start.sh) sets up xvfb and DISPLAY environment variable.
    This function checks if DISPLAY is available and raises an error if headed mode is requested but DISPLAY is not available.
    
    Args:
        headless: Whether to run in headless mode (user preference)
        
    Returns:
        tuple: (actual_headless_value, additional_args)
              - actual_headless_value: True if we should run headless, False for headed
              - additional_args: Additional browser arguments (empty list for now)
              
    Raises:
        RuntimeError: If headed mode is requested but DISPLAY is not available
    """
    # If user explicitly wants headless, use headless
    if headless:
        return True, []
    
    # Check if we're on Linux without a display
    if platform.system() == 'Linux':
        display = os.environ.get('DISPLAY')
        if not display:
            error_msg = (
                "ERROR: Headed mode requested but DISPLAY environment variable is not set.\n"
                "This means xvfb (X Virtual Framebuffer) is not running.\n"
                "The startup script (start.sh) should start xvfb and set DISPLAY=:99.\n"
                "Please check:\n"
                "1. Is xvfb installed? (should be in nixpacks.toml)\n"
                "2. Is start.sh being executed? (check Procfile)\n"
                "3. Are Railway logs showing xvfb startup?\n"
                "Cannot proceed with headed mode - the page requires a display to load correctly."
            )
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)
        else:
            print(f"[INFO] DISPLAY={display} found. Running in headed mode with virtual display.")
            return False, []  # Run in headed mode with xvfb
    
    # Windows/Mac - should have display available
    print("[INFO] Running in headed mode (Windows/Mac detected)")
    return False, []  # Run in headed mode

