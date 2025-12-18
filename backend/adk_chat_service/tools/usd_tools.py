"""USD tools exposed as Google ADK function tools.

These tools are designed to be used with the Google ADK Agent framework.
They communicate with the Kit extension via WebSocket to execute USD operations.

Reference: https://google.github.io/adk-docs/tools-custom/#example-a-simple-math-toolset
"""

from typing import Dict, Any, List, Optional

from ..utils.logger import get_logger

logger = get_logger()


async def raycast_from_camera(max_distance: float = 1000.0) -> Dict[str, Any]:
    """
    Perform raycast from the viewport camera center to find what prim is in the camera's view.

    Use this when the user asks 'what am I looking at' or 'what's in front of the camera'.

    Args:
        max_distance: Maximum raycast distance in scene units (default: 1000)

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - prim_path: Path to the found prim (if success)
            - prim_name: Name of the found prim (if success)
            - prim_type: Type of the found prim (if success)
            - distance: Distance to the prim (if success)
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    try:
        return await kit_manager.call_tool("raycast_from_camera", {"max_distance": max_distance})
    except Exception as e:
        logger.error(f"raycast_from_camera error: {e}")
        return {"success": False, "error": str(e)}


async def get_selection() -> Dict[str, Any]:
    """
    Get the list of currently selected prims in the Omniverse viewport.

    Use this when the user asks about their current selection or what they have selected.

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - selected_prims: List of selected prim info (path, name, type)
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    try:
        return await kit_manager.call_tool("get_selection", {})
    except Exception as e:
        logger.error(f"get_selection error: {e}")
        return {"success": False, "error": str(e)}


async def get_prim_info(prim_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific USD prim.

    Retrieves attributes like position, rotation, scale, visibility, and color.

    Args:
        prim_path: Full USD path to the prim (e.g., '/World/Cube')

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - path: Full prim path
            - name: Prim name
            - type: Prim type
            - attributes: Dict of prim attributes
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    try:
        return await kit_manager.call_tool("get_prim_info", {"prim_path": prim_path})
    except Exception as e:
        logger.error(f"get_prim_info error: {e}")
        return {"success": False, "error": str(e)}


async def get_camera_info() -> Dict[str, Any]:
    """
    Get information about the current viewport camera.

    Returns camera position and direction in world space.

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - camera_path: Path to the camera prim
            - position: Dict with x, y, z coordinates
            - direction: Dict with x, y, z direction vector
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    try:
        return await kit_manager.call_tool("get_camera_info", {})
    except Exception as e:
        logger.error(f"get_camera_info error: {e}")
        return {"success": False, "error": str(e)}


async def create_prim(
    prim_type: str,
    prim_path: str,
    position: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Create a new USD prim (3D object) in the scene.

    Args:
        prim_type: Type of prim to create. Must be one of: Cube, Sphere, Cylinder, Cone, Xform
        prim_path: USD path for the new prim (e.g., '/World/MyCube')
        position: Optional [x, y, z] position for the new prim

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - prim_path: Path to the created prim
            - message: Success message
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    # Validate prim_type
    valid_types = ["Cube", "Sphere", "Cylinder", "Cone", "Xform"]
    if prim_type not in valid_types:
        return {"success": False, "error": f"Invalid prim_type. Must be one of: {valid_types}"}

    params = {"prim_type": prim_type, "prim_path": prim_path}
    if position is not None:
        params["position"] = position

    try:
        return await kit_manager.call_tool("create_prim", params)
    except Exception as e:
        logger.error(f"create_prim error: {e}")
        return {"success": False, "error": str(e)}


async def list_all_prims(root_path: str = "/") -> Dict[str, Any]:
    """
    List all USD prims in the scene under a given root path.

    Useful for understanding scene hierarchy and finding specific prims.

    Args:
        root_path: Root USD path to start listing from (default: '/')

    Returns:
        Dict containing:
            - success: bool indicating if operation succeeded
            - prims: List of prim info (path, name, type)
            - count: Number of prims found
            - error: Error message (if failed)
    """
    from ..services.kit_connection import get_kit_manager

    kit_manager = get_kit_manager()
    if not kit_manager.is_connected:
        return {"success": False, "error": "Kit is not connected"}

    try:
        return await kit_manager.call_tool("list_all_prims", {"root_path": root_path})
    except Exception as e:
        logger.error(f"list_all_prims error: {e}")
        return {"success": False, "error": str(e)}


# List of all USD tools for registration with ADK Agent
USD_TOOLS = [
    raycast_from_camera,
    get_selection,
    get_prim_info,
    get_camera_info,
    create_prim,
    list_all_prims,
]
