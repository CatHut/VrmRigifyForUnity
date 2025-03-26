"""
Constraint Driver Utility Module for VrmRigify Addon

This module provides utility functions for adding drivers to bone constraints
in Blender armatures for more fine-grained control.
"""

import bpy
from typing import Dict, List, Union, Optional


def add_constraint_influence_drivers(
    armature: bpy.types.Object,
    constraint_types: Optional[List[str]] = None,
    collection_name: str = "DEF"
) -> Dict[str, int]:
    """
    Add drivers to control the influence of constraints on DEF bones.
    
    Args:
        armature (bpy.types.Object): The armature object to process
        constraint_types (List[str], optional): List of constraint types to affect.
            If None, all constraints will be affected.
        collection_name (str, optional): Bone collection to filter.
            Defaults to "DEF".
            
    Returns:
        Dict[str, int]: A dictionary of bone names and their processed constraint count
    """
    # Validate armature type
    if armature.type != 'ARMATURE':
        print("Active object is not an armature. Please select an armature.")
        return {}
        
    # Ensure the armature has the custom property for influence control
    if 'constraint_influence' not in armature:
        armature['constraint_influence'] = 1.0
        # Add property metadata for UI
        try:
            ui_data = armature.id_properties_ui('constraint_influence')
            ui_data.update(min=0.0, max=1.0, description="Global influence of DEF bone constraints")
        except (AttributeError, TypeError):
            # Older Blender versions have different API
            pass
    
    # Find the DEF bone collection
    def_collection = None
    for collection in armature.data.collections:
        if collection.name == collection_name:
            def_collection = collection
            break
            
    if not def_collection:
        print(f"{collection_name} bone collection not found. This might not be a Rigify rig.")
        return {}
        
    # Track processed constraints
    result = {}
    
    # Process each bone in the DEF collection
    for bone in armature.pose.bones:
        # Check if bone is in DEF collection
        if (bone.bone and bone.bone.collections and 
            def_collection.name in [c.name for c in bone.bone.collections]):
            
            constraint_count = 0
            
            # Add drivers to each constraint based on specified types
            for constraint in bone.constraints:
                # Skip if constraint type doesn't match the filter (if specified)
                if constraint_types and constraint.type not in constraint_types:
                    continue
                    
                # Skip if the constraint doesn't have an influence property
                if not hasattr(constraint, "influence"):
                    continue
                
                # Create driver for constraint influence
                try:
                    fcurve = constraint.driver_add("influence")
                    driver = fcurve.driver
                    
                    # Create a variable for the armature's custom property
                    var = driver.variables.new()
                    var.name = "influence"
                    var.type = 'SINGLE_PROP'
                    
                    # Set target to the armature's custom property
                    target = var.targets[0]
                    target.id_type = 'OBJECT'
                    target.id = armature
                    target.data_path = '["constraint_influence"]'
                    
                    # Set driver expression to use the variable directly
                    driver.expression = "influence"
                    
                    constraint_count += 1
                except Exception as e:
                    print(f"Error adding driver to {bone.name}.{constraint.name}: {e}")
            
            # Record results
            if constraint_count > 0:
                result[bone.name] = constraint_count
                print(f"{bone.name}: {constraint_count} constraint drivers added.")
    
    # Print summary
    total_constraints = sum(result.values())
    total_bones = len(result)
    print(f"Total: {total_constraints} constraint drivers added across {total_bones} bones.")
    
    return result


def remove_constraint_influence_drivers(
    armature: bpy.types.Object,
    constraint_types: Optional[List[str]] = None,
    collection_name: str = "DEF"
) -> Dict[str, int]:
    """
    Remove drivers controlling the influence of constraints on DEF bones.
    
    Args:
        armature (bpy.types.Object): The armature object to process
        constraint_types (List[str], optional): List of constraint types to affect.
            If None, all constraints will be affected.
        collection_name (str, optional): Bone collection to filter.
            Defaults to "DEF".
            
    Returns:
        Dict[str, int]: A dictionary of bone names and their processed constraint count
    """
    # Validate armature type
    if armature.type != 'ARMATURE':
        print("Active object is not an armature. Please select an armature.")
        return {}
        
    # Find the DEF bone collection
    def_collection = None
    for collection in armature.data.collections:
        if collection.name == collection_name:
            def_collection = collection
            break
            
    if not def_collection:
        print(f"{collection_name} bone collection not found. This might not be a Rigify rig.")
        return {}
        
    # Track processed constraints
    result = {}
    
    # Process each bone in the DEF collection
    for bone in armature.pose.bones:
        # Check if bone is in DEF collection
        if (bone.bone and bone.bone.collections and 
            def_collection.name in [c.name for c in bone.bone.collections]):
            
            constraint_count = 0
            
            # Remove drivers from each constraint based on specified types
            for constraint in bone.constraints:
                # Skip if constraint type doesn't match the filter (if specified)
                if constraint_types and constraint.type not in constraint_types:
                    continue
                    
                # Skip if the constraint doesn't have an influence property
                if not hasattr(constraint, "influence"):
                    continue
                
                # Remove driver for constraint influence
                try:
                    constraint.driver_remove("influence")
                    constraint_count += 1
                except Exception as e:
                    print(f"Error removing driver from {bone.name}.{constraint.name}: {e}")
            
            # Record results
            if constraint_count > 0:
                result[bone.name] = constraint_count
                print(f"{bone.name}: {constraint_count} constraint drivers removed.")
    
    # Print summary
    total_constraints = sum(result.values())
    total_bones = len(result)
    print(f"Total: {total_constraints} constraint drivers removed across {total_bones} bones.")
    
    return result
