"""
Bone Constraint Utility Module for VrmRigify Addon

This module provides utility functions for managing bone constraints in Blender armatures.
"""

import bpy
from typing import Dict, Union


def toggle_def_bone_constraints(
    armature: bpy.types.Object, 
    disable_constraints: bool = True
) -> Dict[str, int]:
    """
    Toggle constraints for bones in the DEF collection.

    Args:
        armature (bpy.types.Object): The armature object to process.
        disable_constraints (bool, optional): Whether to disable or enable constraints. 
            Defaults to True.

    Returns:
        Dict[str, int]: A dictionary of bone names and their processed constraint count.
    """
    # Validate armature type
    if armature.type != 'ARMATURE':
        print("Active object is not an armature. Please select an armature.")
        return {}

    # Find DEF bone collection
    def_collection = None
    for collection in armature.data.collections:
        if collection.name == "DEF":
            def_collection = collection
            break

    # Handle case where DEF collection is not found
    if not def_collection:
        print("DEF bone collection not found. This might not be a Rigify rig.")
        return {}

    # Track processed constraints
    result = {}

    # Process constraints for DEF collection bones
    for bone in armature.pose.bones:
        # Check if bone is in DEF collection
        if (bone.bone and bone.bone.collections and 
            def_collection.name in [c.name for c in bone.bone.collections]):
            
            constraint_count = 0
            # Toggle constraints
            for constraint in bone.constraints:
                constraint.mute = disable_constraints
                constraint_count += 1
            
            # Record results
            if constraint_count > 0:
                result[bone.name] = constraint_count
                action_text = "disabled" if disable_constraints else "enabled"
                print(f"{bone.name}: {constraint_count} constraints {action_text}.")

    # Print summary
    total_constraints = sum(result.values())
    total_bones = len(result)
    action_text = "disabled" if disable_constraints else "enabled"
    print(f"Total: {total_constraints} constraints {action_text} across {total_bones} bones.")

    return result


def get_bone_constraints(
    armature: bpy.types.Object, 
    bone_name: str = None, 
    collection_name: str = "DEF"
) -> Union[Dict[str, list], list]:
    """
    Retrieve constraints for bones in a specific collection.

    Args:
        armature (bpy.types.Object): The armature object to process.
        bone_name (str, optional): Specific bone name to get constraints for. 
            If None, returns constraints for all bones in the collection.
        collection_name (str, optional): Bone collection to filter. 
            Defaults to "DEF".

    Returns:
        Union[Dict[str, list], list]: Constraints for specified bone(s)
    """
    if armature.type != 'ARMATURE':
        print("Active object is not an armature.")
        return []

    # Find bone collection
    target_collection = None
    for collection in armature.data.collections:
        if collection.name == collection_name:
            target_collection = collection
            break

    if not target_collection:
        print(f"Collection '{collection_name}' not found.")
        return []

    # Process constraints
    constraints_map = {}
    for bone in armature.pose.bones:
        # Check bone collection
        if (bone.bone and bone.bone.collections and 
            target_collection.name in [c.name for c in bone.bone.collections]):
            
            # If specific bone is requested
            if bone_name and bone.name != bone_name:
                continue

            # Collect constraints
            bone_constraints = [
                {
                    'type': constraint.type, 
                    'name': constraint.name, 
                    'muted': constraint.mute
                } 
                for constraint in bone.constraints
            ]

            if bone_name:
                return bone_constraints

            constraints_map[bone.name] = bone_constraints

    return constraints_map


