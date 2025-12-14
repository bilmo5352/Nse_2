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
    This function checks if DISPLAY is available and adjusts headless mode accordingly.
    
    Args:
        headless: Whether to run in headless mode (user preference)
        
    Returns:
        tuple: (actual_headless_value, additional_args)
              - actual_headless_value: True if we should run headless, False for headed
              - additional_args: Additional browser arguments (empty list for now)
    """
    # If user explicitly wants headless, use headless
    if headless:
        return True, []
    
    # Check if we're on Linux without a display
    if platform.system() == 'Linux':
        display = os.environ.get('DISPLAY')
        if not display:
            print("[WARN] No DISPLAY environment variable found on Linux.")
            print("[WARN] xvfb should be started by the startup script.")
            print("[WARN] Falling back to headless mode to prevent errors.")
            return True, []  # Fallback to headless to prevent crashes
        else:
            print(f"[INFO] DISPLAY={display} found. Running in headed mode with virtual display.")
            return False, []  # Run in headed mode with xvfb
    
    # Windows/Mac - should have display available
    return False, []  # Run in headed mode

