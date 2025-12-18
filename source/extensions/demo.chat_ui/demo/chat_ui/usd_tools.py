"""USD and viewport tools exposed as MCP tools."""

import omni.usd
from omni.kit.viewport.utility import get_active_viewport_camera_string
from pxr import Gf, UsdGeom, Usd
import carb
from typing import Dict, Any, List, Optional


class USDTools:
    """Collection of USD manipulation and query tools."""

    @staticmethod
    def raycast_from_camera(max_distance: float = 1000.0) -> Dict[str, Any]:
        """
        Perform raycast from camera center to find the prim in view.

        Args:
            max_distance: Maximum raycast distance

        Returns:
            Dict with prim info or error
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()

            if not stage:
                return {"success": False, "error": "No stage loaded"}

            # Get camera
            camera_path = get_active_viewport_camera_string()
            camera_prim = stage.GetPrimAtPath(camera_path)

            if not camera_prim.IsValid():
                return {"success": False, "error": "No valid camera found"}

            # Get camera transform
            xformAPI = UsdGeom.XformCache()
            camera_matrix = xformAPI.GetLocalToWorldTransform(camera_prim)

            # Camera position and direction
            ray_origin = camera_matrix.ExtractTranslation()
            ray_direction = camera_matrix.TransformDir(Gf.Vec3d(0, 0, -1)).GetNormalized()
            ray = Gf.Ray(ray_origin, ray_direction)

            # Find closest intersecting prim
            closest_prim = None
            closest_distance = max_distance

            for prim in stage.Traverse():
                # Skip non-geometric prims
                if not prim.IsA(UsdGeom.Imageable):
                    continue
                if prim.GetName().startswith('OmniverseKit_'):
                    continue

                # Check bounding box intersection
                if prim.IsA(UsdGeom.Boundable):
                    bound = UsdGeom.Boundable(prim).ComputeWorldBound(
                        Usd.TimeCode.Default(), "default"
                    )
                    bbox = bound.GetBox()

                    if not bbox.IsEmpty():
                        intersection = bbox.ComputeNearestPoint(ray_origin)
                        distance = (intersection - ray_origin).GetLength()

                        # Check if ray passes through bbox
                        ray_to_box = (intersection - ray_origin).GetNormalized()
                        dot_product = Gf.Dot(ray_to_box, ray_direction)

                        if dot_product > 0.9 and distance < closest_distance:
                            closest_distance = distance
                            closest_prim = prim

            if closest_prim:
                return {
                    "success": True,
                    "prim_path": str(closest_prim.GetPath()),
                    "prim_name": closest_prim.GetName(),
                    "prim_type": closest_prim.GetTypeName(),
                    "distance": closest_distance
                }

            return {"success": False, "error": "No prim found in camera view"}

        except Exception as e:
            carb.log_error(f"Raycast error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_selection() -> Dict[str, Any]:
        """
        Get currently selected prims.

        Returns:
            Dict with selected prim paths and info
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()
            selection = ctx.get_selection()

            selected_paths = selection.get_selected_prim_paths()

            if not selected_paths:
                return {"success": True, "selected_prims": []}

            prims_info = []
            for path in selected_paths:
                prim = stage.GetPrimAtPath(path)
                if prim.IsValid():
                    prims_info.append({
                        "path": str(prim.GetPath()),
                        "name": prim.GetName(),
                        "type": prim.GetTypeName()
                    })

            return {"success": True, "selected_prims": prims_info}

        except Exception as e:
            carb.log_error(f"Get selection error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_prim_info(prim_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific prim.

        Args:
            prim_path: USD path to the prim

        Returns:
            Dict with prim details
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()

            prim = stage.GetPrimAtPath(prim_path)

            if not prim.IsValid():
                return {"success": False, "error": f"Prim not found: {prim_path}"}

            # Get attributes
            attributes = {}
            for attr in prim.GetAttributes():
                attr_name = attr.GetName()
                # Only include commonly useful attributes
                if attr_name in ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale",
                                "visibility", "purpose", "displayColor"]:
                    attributes[attr_name] = str(attr.Get())

            return {
                "success": True,
                "path": str(prim.GetPath()),
                "name": prim.GetName(),
                "type": prim.GetTypeName(),
                "attributes": attributes
            }

        except Exception as e:
            carb.log_error(f"Get prim info error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_camera_info() -> Dict[str, Any]:
        """
        Get current viewport camera information.

        Returns:
            Dict with camera position, rotation, and target info
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()

            camera_path = get_active_viewport_camera_string()
            camera_prim = stage.GetPrimAtPath(camera_path)

            if not camera_prim.IsValid():
                return {"success": False, "error": "No valid camera found"}

            # Get camera transform
            xformAPI = UsdGeom.XformCache()
            camera_matrix = xformAPI.GetLocalToWorldTransform(camera_prim)

            position = camera_matrix.ExtractTranslation()
            direction = camera_matrix.TransformDir(Gf.Vec3d(0, 0, -1))

            return {
                "success": True,
                "camera_path": str(camera_path),
                "position": {"x": position[0], "y": position[1], "z": position[2]},
                "direction": {"x": direction[0], "y": direction[1], "z": direction[2]}
            }

        except Exception as e:
            carb.log_error(f"Get camera info error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_prim(prim_type: str, prim_path: str, position: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Create a new prim in the stage.

        Args:
            prim_type: Type of prim (e.g., "Cube", "Sphere", "Xform")
            prim_path: USD path for the new prim
            position: Optional [x, y, z] position

        Returns:
            Dict with creation result
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()

            # Map common names to UsdGeom types
            type_map = {
                "Cube": UsdGeom.Cube,
                "Sphere": UsdGeom.Sphere,
                "Cylinder": UsdGeom.Cylinder,
                "Cone": UsdGeom.Cone,
                "Xform": UsdGeom.Xform
            }

            if prim_type not in type_map:
                return {"success": False, "error": f"Unknown prim type: {prim_type}"}

            # Create prim
            prim_class = type_map[prim_type]
            new_prim = prim_class.Define(stage, prim_path)

            # Set position if provided
            if position and len(position) == 3:
                xformable = UsdGeom.Xformable(new_prim)
                xformable.AddTranslateOp().Set(Gf.Vec3d(position[0], position[1], position[2]))

            return {
                "success": True,
                "prim_path": str(new_prim.GetPath()),
                "message": f"Created {prim_type} at {prim_path}"
            }

        except Exception as e:
            carb.log_error(f"Create prim error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_all_prims(root_path: str = "/") -> Dict[str, Any]:
        """
        List all prims under a given root path.

        Args:
            root_path: Root USD path to start listing from

        Returns:
            Dict with list of prim paths and types
        """
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()

            root_prim = stage.GetPrimAtPath(root_path)
            if not root_prim.IsValid():
                return {"success": False, "error": f"Invalid root path: {root_path}"}

            prims = []
            for prim in Usd.PrimRange(root_prim):
                # Skip system prims
                if prim.GetName().startswith('OmniverseKit_'):
                    continue

                prims.append({
                    "path": str(prim.GetPath()),
                    "name": prim.GetName(),
                    "type": prim.GetTypeName()
                })

            return {
                "success": True,
                "prims": prims,
                "count": len(prims)
            }

        except Exception as e:
            carb.log_error(f"List prims error: {e}")
            return {"success": False, "error": str(e)}
