#################################################
# This addon is based on the work by R workshop
# Original work: https://booth.pm/ja/items/5448887
# Original license: MIT License (https://opensource.org/licenses/mit-license.php)
#################################################

bl_info = {
    "name": "VrmRigifyForUnity",
    "author": "CatHut",
    "version": (1, 0, 0),  # Version updated to reflect new feature
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > VRM",
    "description": "Generate and modify RigifyRig from VRM model for Unity",
    "warning": "",
    "doc_url": "",
    "category": "Rigging",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty, FloatProperty

# Import functions from vrm_rigify module
from . import vrm_rigify
from . import bone_constraint_utils
from . import constraint_driver_utils


#################################################
# メインオペレータークラス（VRM to Rigify変換）
#################################################

class VRM_OT_ToRigify(Operator):
    """Generate and modify RigifyRig from VRM model"""
    bl_idname = "vrm.to_rigify"
    bl_label = "Generate Rigify from VRM"
    bl_options = {'REGISTER', 'UNDO'}
    
    hide_original: BoolProperty(
        name="Hide Original Model",
        description="Hide the original VRM model after generating Rigify",
        default=True
    )
    
    hide_metarig: BoolProperty(
        name="Hide Metarig",
        description="Hide the metarig after generating Rigify",
        default=True
    )
    
    copy_vrm_settings: BoolProperty(
        name="Copy VRM Settings",
        description="Copy VRM settings from original armature to Rigify armature",
        default=True
    )
    
    setup_constraint_drivers: BoolProperty(
        name="Setup Constraint Drivers",
        description="Add influence drivers to the DEF bones constraints for easy adjustment",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        # アクティブオブジェクトがアーマチュアかどうかをチェック
        return context.active_object and context.active_object.type == 'ARMATURE'
    
    def execute(self, context):
        # 現在のアクティブオブジェクト（VRMモデル）を取得
        vrm_object = context.active_object
        
        try:
            # オリジナルのボーン名を保存
            original_bone_names = vrm_rigify.store_original_bone_names(vrm_object)
            
            # メインの変換プロセスを実行
            vrm_rigify.rename_vrm_model_bones_name(vrm_object)
            
            # 標準化後のボーン名とオリジナルボーン名のマッピングを更新
            bone_name_mapping = vrm_rigify.update_bone_name_mapping_after_rename(
                vrm_object, original_bone_names)
            
            # debug
            vrm_rigify.debug_bone_name_mapping(original_bone_names, bone_name_mapping, vrm_object)
            
            # メタリグを生成
            metarig_name = f"{vrm_object.name}.metarig"
            metarig = vrm_rigify.generate_template_metarig(metarig_name)
            
            # ボーンのマッピングと位置合わせ
            bone_mapping = vrm_rigify.mapping_metarig_and_vrm_model_bones(metarig, vrm_object)
            vrm_rigify.remove_or_log_unmapped_metarig_bones(metarig, bone_mapping)
            vrm_rigify.position_metarig_bones_to_vrm_model(metarig, vrm_object, bone_mapping)
            
            # メタリグの調整
            vrm_rigify.adjust_position_of_metarig_spine_bones(metarig)
            vrm_rigify.Modify_metarig_limb_rotation_axes(metarig)
            vrm_rigify.modify_metarig_arm_hand_finger_rotation(metarig)
            vrm_rigify.modify_metarig_limb_segments(metarig)
            
            # Rigifyリグを生成
            rig_object = vrm_rigify.generate_rigify_rig(metarig)
            
            # リグの処理と調整
            vrm_rigify.removed_rigify_rig_facial_bones(rig_object)
            vrm_rigify.rename_rig_bones_to_match_vrm_model_vertex_groups(rig_object, bone_mapping, bone_name_mapping)

            # debug
            vrm_rigify.debug_attach_unmapped_bones(rig_object, vrm_object, bone_name_mapping)

            vrm_rigify.attach_unmapped_vrm_model_bones_to_rig(rig_object, vrm_object, bone_name_mapping)
            vrm_rigify.copy_shape_key_controls_from_vrm_armature(rig_object, vrm_object)
            
            # リグのボーン調整
            vrm_rigify.modify_rigify_rig_eyes_control_bones(rig_object)
            vrm_rigify.disable_ik_stretching(rig_object)
            vrm_rigify.show_ik_toggle_pole(rig_object)
            
            # メッシュのコピーと設定
            vrm_rigify.copy_meshes_between_armatures(vrm_object, rig_object, bone_name_mapping)
            vrm_rigify.change_meshes_modifier_object(rig_object)

            # 親子関係など最終調整
            vrm_rigify.adjust_bone_hierarchy_and_constraints_for_Unity(rig_object)

            # 元のArmatureのボーン名を元に戻す
            vrm_rigify.restore_original_bone_names(vrm_object, original_bone_names)

            # コンストレイントドライバーのセットアップ
            if self.setup_constraint_drivers:
                vrm_rigify.setup_rig_constraint_drivers(rig_object)

            # VRM拡張情報をコピーするかどうかのチェック
            if self.copy_vrm_settings:
                # VRM拡張情報のコピー（新機能）
                from . import vrm_extension_utils
                vrm_extension_utils.copy_vrm_extension_from_armature(vrm_object, rig_object)
    
            
            # オブジェクトの表示設定（リクエストに応じて非表示）
            if self.hide_metarig:
                metarig.hide_set(True)
                metarig.hide_render = True
                
            if self.hide_original:
                for vrm_child in vrm_object.children:
                    if vrm_child.type == 'MESH':
                        vrm_child.hide_set(True)
                        vrm_child.hide_render = True
                vrm_object.hide_set(True)
                vrm_object.hide_render = True
            
            # 最終設定
            rig_object.show_in_front = True
            
            # 新しいリグを選択し、アクティブに設定
            bpy.ops.object.select_all(action='DESELECT')
            rig_object.select_set(True)
            context.view_layer.objects.active = rig_object
            
            self.report({'INFO'}, "VRM to Rigify conversion complete")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}


#################################################
# コンストレイント操作オペレーター
#################################################

class VRM_OT_ToggleConstraintDrivers(Operator):
    """Toggle constraint drivers between ON and OFF"""
    bl_idname = "vrm.toggle_constraint_drivers"
    bl_label = "Toggle Constraint Drivers"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode: StringProperty(
        name="Mode",
        description="Whether to add or remove constraint drivers",
        default="ADD"
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'
    
    def execute(self, context):
        armature = context.active_object
        
        if self.mode == "ADD":
            result = setup_constraint_drivers.setup_rig_constraint_drivers(armature)
            if result:
                self.report({'INFO'}, "Constraint drivers added successfully")
            else:
                self.report({'WARNING'}, "No constraint drivers were added")
        else:  # REMOVE
            result = constraint_driver_utils.remove_constraint_influence_drivers(armature)
            if result:
                self.report({'INFO'}, "Constraint drivers removed successfully")
            else:
                self.report({'WARNING'}, "No constraint drivers were removed")
        
        return {'FINISHED'}


#################################################
# UIパネルクラス
#################################################

class VRM_PT_ToRigifyPanel(Panel):
    """Panel for VrmRigify conversion"""
    bl_label = "VrmRigifyForUnity"
    bl_idname = "VRM_PT_to_rigify"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VRM'
    
    def draw(self, context):
        layout = self.layout
        
        # Rigifyアドオンが有効かどうかをチェック
        rigify_enabled = 'rigify' in [addon.module for addon in bpy.context.preferences.addons]
        
        if not rigify_enabled:
            layout.label(text="Rigify add-on not enabled", icon='ERROR')
            layout.operator("preferences.addon_enable", text="Enable Rigify").module = 'rigify'
        
        # 現在の選択情報を表示
        obj = context.active_object
        if obj:
            layout.label(text=f"Selected: {obj.name}")
            layout.label(text=f"Type: {obj.type}")
            
            if obj.type == 'ARMATURE':
                # VRMからRigifyへの変換設定
                box = layout.box()
                box.label(text="Conversion Settings:")
                col = box.column()
                op = col.operator("vrm.to_rigify")
                col.prop(op, "hide_original")
                col.prop(op, "hide_metarig")
                col.prop(op, "copy_vrm_settings")
                col.prop(op, "setup_constraint_drivers")
                
                # Rigifyリグ操作エリア
                box = layout.box()
                box.label(text="Rigify Controls:")
                
                # コンストレイントドライバー関連の操作UI
                has_constraint_influence = 'constraint_influence' in obj
                
                # コンストレイント影響度のスライダー
                if has_constraint_influence:
                    box.prop(obj, '["constraint_influence"]', slider=True, text="Constraint Influence")
                
                # ON/OFF切り替え機能
                box.prop(context.scene, "vrm_rigify_disable_control_rig", toggle=True)
                
                # ドライバの追加/削除ボタン
                row = box.row(align=True)
                row.operator("vrm.toggle_constraint_drivers", text="Add Drivers").mode = "ADD"
                row.operator("vrm.toggle_constraint_drivers", text="Remove Drivers").mode = "REMOVE"
            else:
                layout.label(text="Select a VRM Armature", icon='ARMATURE_DATA')
        else:
            layout.label(text="No object selected", icon='OBJECT_DATA')


#################################################
# アドオン登録
#################################################

# シーンプロパティの登録
def register_properties():
    bpy.types.Scene.vrm_rigify_disable_control_rig = BoolProperty(
        name="Disable Control Rig",
        description="DEFボーンのコンストレイントを無効化し、直接ボーンを動かせるようにします",
        default=False,
        update=lambda self, context: bone_constraint_utils.toggle_def_bone_constraints(
            context.active_object, 
            self.vrm_rigify_disable_control_rig
        ) if context.active_object and context.active_object.type == 'ARMATURE' else None
    )

def unregister_properties():
    del bpy.types.Scene.vrm_rigify_disable_control_rig

classes = (
    VRM_OT_ToRigify,
    VRM_OT_ToggleConstraintDrivers,
    VRM_PT_ToRigifyPanel,
)

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()