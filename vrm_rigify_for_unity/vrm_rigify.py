#################################################
# This addon is based on the work by R workshop
# Original work: https://booth.pm/ja/items/5448887
# Original license: MIT License (https://opensource.org/licenses/mit-license.php)
#################################################


import re
import math

import bpy
from . import bone_constraint_utils
from . import constraint_driver_utils

#################################################
#region ユーティリティクラスと関数
#################################################

class ModeContext:
    """
    Blenderのオブジェクトモード（編集モード、ポーズモードなど）を
    コンテキストマネージャーとして扱うためのクラス
    
    使用例:
    with ModeContext("EDIT"):
        # 編集モードでの操作
    # 自動的に元のモードに戻る
    """
    
    def __init__(self, mode):
        self.mode = mode  # 設定したいモード（"EDIT", "POSE", "OBJECT"など）

    def __enter__(self):
        # 現在のモードを保存して、指定されたモードに切り替え
        self.old_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode=self.mode)

    def __exit__(self, _type, _value, _trace):
        # 元のモードに戻す
        bpy.ops.object.mode_set(mode=self.old_mode)

    @staticmethod
    def editing(node: bpy.types.Object):
        """
        指定されたオブジェクトを選択して編集モードにするショートカットメソッド
        """
        node.select_set(True)
        return ModeContext("EDIT")


def blender_version():
    """
    現在のBlenderのメジャーバージョンを取得する関数
    """
    blender_version = bpy.app.version
    major_version = blender_version[0]
    minor_version = blender_version[1]
    return major_version

def matche_objects_by_name_patterns(objects, patterns: list[str]) -> list[object]:
    """
    正規表現パターンに一致するオブジェクトを検索する関数
    
    Args:
        objects: 検索対象のオブジェクトのコレクション
        patterns: 正規表現パターンのリスト
        
    Returns:
        一致するオブジェクトのリスト
    """
    object_matches = []
    for node in objects:
        matches = False
        for pattern in patterns:
            matches |= bool(re.match(pattern, node.name))
        if matches:
            object_matches.append(node)

    return object_matches


def get_full_bone_path(bone: bpy.types.Bone | bpy.types.EditBone) -> str:
    """
    ボーンの完全なパス（親の階層を含む）を取得する関数
    
    Args:
        bone: パスを取得するボーン
        
    Returns:
        ボーンのフルパス（例: 'parent/child/grandchild'）
    """
    bone_chain = list(reversed(bone.parent_recursive)) + [bone]
    return '/'.join([bone.name for bone in bone_chain])

#endregion

#################################################
#region メタリグと基本設定関連の関数
#################################################

def generate_template_metarig(metarig_name: str) -> bpy.types.Object:
    """
    Rigifyのテンプレートメタリグを生成する関数
    
    Args:
        metarig_name: 生成するメタリグの名前
        
    Returns:
        生成されたメタリグオブジェクト
        
    Raises:
        Exception: Rigifyアドオンが有効でない場合
    """
    try:
        bpy.ops.object.armature_human_metarig_add()
        metarig = bpy.context.view_layer.objects.active
        metarig.name = metarig_name
        metarig.data.name = metarig_name
        return metarig
    except AttributeError as e:
        raise Exception(
            "Failed to spawn metarig. Is the Rigify addon enabled?") from e
    

def modify_metarig_limb_segments(metarig: bpy.types.Object):
    """
    メタリグの腕と脚のセグメント数を1に設定する関数
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
    """
    # 調整対象のリムボーン（腕・脚）のリスト
    limb_bones = [
        "upper_arm.R",
        "upper_arm.L",
        "thigh.R",
        "thigh.L",
    ]

    pose_bones = metarig.pose.bones
    
    # 腕と脚のセグメント数を1に設定
    for bone_name in limb_bones:
        if bone_name in pose_bones:
            bone = pose_bones[bone_name]
            if hasattr(bone, "rigify_parameters") and hasattr(bone.rigify_parameters, "segments"):
                # print(f"Setting segments to 1 for {bone_name}")
                bone.rigify_parameters.segments = 1
    

def rename_vrm_model_bones_name(vrm_object):
    """
    VRMモデルのボーン名を標準化する関数
    VRM形式で使用される標準的なボーン名に変更する
    """
    vrm_armature = vrm_object.data # edit_boneの取得に必要

    bpy.ops.vrm.bones_rename(armature_name="Armature")


def store_original_bone_names(vrm_object) -> dict:
    """
    VRMモデルのオリジナルのボーン名を保存する関数
    
    Args:
        vrm_object: VRMモデルのアーマチュアオブジェクト
        
    Returns:
        オリジナルボーン名と標準化後のボーン名のマッピング辞書
    """
    armature_vrm = vrm_object.data
    original_bone_names = {}
    
    # オリジナルのボーン名を保存
    for bone in armature_vrm.bones:
        original_bone_names[bone.name] = bone.name
    
    return original_bone_names


def restore_original_bone_names(vrm_object, original_bone_names):
    """
    VRMモデルのボーン名を元の名前に戻す関数
    
    Args:
        vrm_object: VRMモデルのアーマチュアオブジェクト
        original_bone_names: オリジナルのボーン名の辞書
    """
    armature_vrm = vrm_object.data
    
    # 編集モードでボーン名を元に戻す
    with ModeContext.editing(vrm_object):
        for i, bone in enumerate(armature_vrm.edit_bones):
            if i in range(len(original_bone_names.values())):
                original_name = list(original_bone_names.values())[i]
                bone.name = original_name


def update_bone_name_mapping_after_rename(vrm_object, original_bone_names) -> dict:
    """
    ボーン名の標準化後にマッピングを更新する関数
    
    Args:
        vrm_object: VRMモデルのアーマチュアオブジェクト
        original_bone_names: オリジナルボーン名の辞書
        
    Returns:
        更新されたマッピング辞書 {標準化後のボーン名: オリジナルのボーン名}
    """
    armature_vrm = vrm_object.data
    bone_name_mapping = {}
    
    # まず、全てのオリジナルボーンのインデックスを記録
    bone_indices = {}
    for i, bone_name in enumerate(original_bone_names.keys()):
        bone_indices[i] = bone_name
    
    # 標準化後のボーンとオリジナルボーンのマッピングを作成
    # インデックスベースでマッピングを行う（順序は変わらないと仮定）
    for i, bone in enumerate(armature_vrm.bones):
        if i in bone_indices:
            original_name = bone_indices[i]
            # 標準化後の名前をキー、オリジナルの名前を値とする
            bone_name_mapping[bone.name] = original_name
    
    return bone_name_mapping

#endregion


#################################################
#region ボーンマッピングと位置合わせの関数
#################################################

def mapping_metarig_and_vrm_model_bones(
        metarig: bpy.types.Object, vrm_object: bpy.types.Object) -> list:
    """
    メタリグとVRMモデルのボーンをマッピングする関数
    
    VRMの人間ボーン定義を使用して、メタリグのボーンとVRMモデルのボーンの対応関係を作成する
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
        vrm_object: VRMモデルのアーマチュアオブジェクト
        
    Returns:
        (メタリグのボーン名, VRMモデルのボーン名)のタプルのリスト
    """
    # 自動的にVRM1のヒューマノイドボーンを割り当て
    bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(
        armature_name = metarig.name
    )

    bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(
        armature_name = vrm_object.name
    )

    # VRM拡張データからヒューマノイドボーン情報を取得
    armature_metarig: bpy.types.Armature = metarig.data
    armature_vrm    : bpy.types.Armature = vrm_object.data
    metarig_human_bones = armature_metarig.vrm_addon_extension.vrm1.humanoid.human_bones
    vrm_human_bones     = armature_vrm.vrm_addon_extension.vrm1.humanoid.human_bones

    # マッピングリストを作成
    bone_mapping = []
    for bone_type in metarig_human_bones.keys():
        if bone_type in ["last_bone_names", "initial_automatic_bone_assignment"]:
            continue

        metarig_bone_attr = getattr(metarig_human_bones, bone_type, None)
        vrm_bone_attr = getattr(vrm_human_bones, bone_type, None)

        if (
            hasattr(metarig_bone_attr, "node") and
            hasattr(vrm_bone_attr, "node")
        ):
            metarig_bone = metarig_bone_attr.node
            vrm_bone = vrm_bone_attr.node
            if hasattr(vrm_bone, "bone_name") and vrm_bone.bone_name:
                bone_mapping.append((metarig_bone.bone_name, vrm_bone.bone_name))

    return bone_mapping


def remove_or_log_unmapped_metarig_bones(metarig: bpy.types.Object, bone_mapping):
    """
    VRMモデルにマッピングされていないメタリグのボーンを削除または記録する関数
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
        bone_mapping: ボーンマッピングのリスト（mapping_metarig_and_vrm_model_bones関数の戻り値）
    """
    # マッピングされているメタリグのボーン名のセット
    mapped_metarig_bone_names = set(
        [metarig_bone for metarig_bone, vrm_bone in bone_mapping])
    armature_metarig: bpy.types.Armature = metarig.data

    with ModeContext.editing(metarig):
        # palm（手のひら）ボーンを削除
        for metarig_bone in matche_objects_by_name_patterns(
                                    armature_metarig.edit_bones, [r"^palm.*$"]):
            # print(f"removing: metarig palm bone'{metarig_bone.name}'")
            armature_metarig.edit_bones.remove(metarig_bone)
        
        # その他のボーンを処理（未マッピングのものは削除またはログ）
        for metarig_bone in armature_metarig.edit_bones:
            if metarig_bone.name in mapped_metarig_bone_names:
                continue
            if metarig_bone.name in ["pelvis.L", "pelvis.R"]:
                # print(f"removing: metarig pelvis bone'{metarig_bone.name}'")
                armature_metarig.edit_bones.remove(metarig_bone)
                continue
            if metarig_bone.name in ["breast.L", "breast.R"]:
                # print(f"removing: can't be used in VRM'{get_full_bone_path(metarig_bone)}'")
                armature_metarig.edit_bones.remove(metarig_bone)
                continue
            if metarig_bone.name not in ["spine.003"]:
                # print(f"metarig bone is not mapped '{get_full_bone_path(metarig_bone)}'")
                continue

            # print(f"removing: unmapped metarig bone'{get_full_bone_path(metarig_bone)}'")
            armature_metarig.edit_bones.remove(metarig_bone)


def position_metarig_bones_to_vrm_model(
        metarig: bpy.types.Object, vrm_object: bpy.types.Object, bone_mapping):
    """
    メタリグのボーンをVRMモデルのボーンの位置に合わせる関数
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
        vrm_object: VRMモデルのアーマチュアオブジェクト
        bone_mapping: ボーンマッピングのリスト
    """
    armature_metarig: bpy.types.Armature = metarig.data
    armature_vrm: bpy.types.Armature = vrm_object.data

    with ModeContext.editing(metarig):
        # メタリグの変換行列をVRMモデルに合わせる
        metarig.matrix_world = vrm_object.matrix_world
        
        # 各ボーンの位置合わせ
        for metarig_bone_name, vrm_bone_name in bone_mapping:
            metarig_bone = armature_metarig.edit_bones[metarig_bone_name]
            vrm_bone = armature_vrm.bones[vrm_bone_name]

            # print(f"positioning   '{get_full_bone_path(metarig_bone)}'")
            # print(f"            to'{get_full_bone_path(vrm_bone)}'")
            metarig_bone.select = True
            metarig_bone.head = vrm_bone.head_local
            metarig_bone.tail = vrm_bone.tail_local

#endregion

#################################################
#region メタリグボーンの調整関数
#################################################

def adjust_position_of_metarig_spine_bones(metarig: bpy.types.Object):
    """
    メタリグの脊椎ボーンの位置を調整する関数
    特に首の付け根あたりのボーン接続を調整
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
    """
    armature_metarig: bpy.types.Armature = metarig.data
    with ModeContext.editing(metarig):
        # spine.004はネックボーン（首）の付け根
        # 一度接続してから切断することで位置調整を行う
        armature_metarig.edit_bones["spine.004"].use_connect = True
        armature_metarig.edit_bones["spine.004"].use_connect = False


def Modify_metarig_limb_rotation_axes(metarig: bpy.types.Object):
    """
    メタリグの腕や脚の回転軸を調整する関数
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
    """
    # 調整対象のリムボーン（腕・脚）パターン
    limb_bones = [
        r"^upper_arm\.(L|R)$",  # 上腕
        r"^thigh\.(L|R)$",      # 太もも
    ]

    # 調整対象の指ボーンパターン
    finger_bones = [
        r"^f_pinky\.01\.(L|R)$",   # 小指
        r"^f_ring\.01\.(L|R)$",    # 薬指
        r"^f_middle\.01\.(L|R)$",  # 中指
        r"^f_index\.01\.(L|R)$",   # 人差し指
        r"^thumb\.01\.(L|R)$",     # 親指
    ]

    pose_bones = metarig.pose.bones
    
    # 腕と脚の回転軸をx軸に設定
    for bone in matche_objects_by_name_patterns(pose_bones, limb_bones):
        # print(f"Modify limb bone rotation axis(arm,thigh) '{bone.name}'")
        bone.rigify_parameters.rotation_axis = 'x'

    # 指の回転軸を設定（左右で異なる方向）
    for bone in matche_objects_by_name_patterns(pose_bones, finger_bones):
        # print(f"Modify limb bone rotation axis(finger,thumb) '{bone.name}'")
        axis = 'Z' if bone.name.endswith('L') else '-Z'
        bone.rigify_parameters.primary_rotation_axis = axis


def modify_metarig_arm_hand_finger_rotation(metarig: bpy.types.Object):
    """
    メタリグの腕、手、指の回転を調整する関数
    ボーンのroll値（回転）を調整して自然な動きを実現する
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
    """
    with ModeContext.editing(metarig):
        edit_bones = metarig.data.edit_bones
        for bone in edit_bones:
            # 指のボーンの回転調整
            if bone.name.startswith("f_") and ".L" in bone.name:
                bone.roll = math.radians(-90)  # 左手の指は-90度回転              
            if bone.name.startswith("f_") and ".R" in bone.name:
                bone.roll = math.radians(90)   # 右手の指は90度回転
            if bone.name.startswith("thumb"):
                bone.roll = math.radians(0)    # 親指はロールなし              

            # 腕と手のボーンの回転調整
            if (("arm" in bone.name and ".L" in bone.name)
                or ("hand" in bone.name and ".L" in bone.name)):
                bone.roll = math.radians(90)   # 左腕・左手は90度回転                  
            if (("arm" in bone.name and ".R" in bone.name)
                or ("hand" in bone.name and ".R" in bone.name)):
                bone.roll = math.radians(-90)  # 右腕・右手は-90度回転

#endregion

#################################################
#region Rigifyリグの生成と調整関数
#################################################

def generate_rigify_rig(metarig: bpy.types.Object) -> bpy.types.Object:
    """
    メタリグからRigifyリグを生成する関数
    
    Args:
        metarig: Rigifyのメタリグオブジェクト
        
    Returns:
        生成されたRigifyリグオブジェクト
    """
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.pose.rigify_generate()
    return bpy.context.view_layer.objects.active


def removed_rigify_rig_facial_bones(rig_object: bpy.types.Object):
    """
    Rigifyリグの顔部分のボーンを削除する関数
    VRMモデルでは顔のリギングが異なるため不要なボーンを削除
    
    Args:
        rig_object: Rigifyリグオブジェクト
    """
    # 削除対象の顔ボーンパターン
    rig_bones_to_delete_by_name_pattern = [
        r"^(ORG|DEF)-forehead.*$",       # 額
        r"^(ORG|DEF)-temple.*$",         # こめかみ
        r"^((ORG|DEF)-)?brow.*$",        # 眉
        r"^((MCH|ORG|DEF)-)?lid\.(B|T).*$", # まぶた
        r"^((ORG|DEF)-)?ear\.(L|R).*$",  # 耳
        r"^((MCH|ORG|DEF)-)?tongue.*$",  # 舌
        r"^((ORG|DEF)-)?chin.*$",        # あご
        r"^((ORG|DEF)-)?cheek\.(B|T).*$", # 頬
        r"^(ORG-)?teeth\.(B|T)$",        # 歯
        r"^((ORG|DEF)-)?nose.*$",        # 鼻
        r"^((ORG|DEF)-)?lip.*$",         # 唇
        r"^((MCH|ORG|DEF)-)?jaw.*$",     # 顎
        r"^MCH-mouth_lock$",             # 口制御
    ]

    armature_rig: bpy.types.Armature = rig_object.data
    with ModeContext.editing(rig_object):
        bones_to_remove = []
        # 削除対象のボーンとその子孫ボーンを集める
        for bone_root in matche_objects_by_name_patterns(
            armature_rig.edit_bones, rig_bones_to_delete_by_name_pattern):

            for bone in bone_root.children_recursive + [bone_root]:
                if bone not in bones_to_remove:
                    bones_to_remove.append(bone)

        # ボーンを削除
        for bone in bones_to_remove:
            # print(f"deleting facial bone '{get_full_bone_path(bone)}'")
            armature_rig.edit_bones.remove(bone)


def rename_rig_bones_to_match_vrm_model_vertex_groups(
        rig_object: bpy.types.Object, bone_mapping, bone_name_mapping=None):
    """
    Rigifyリグのボーン名をVRMモデルの頂点グループ名に合わせる関数
    
    Args:
        rig_object: Rigifyリグオブジェクト
        bone_mapping: ボーンマッピングのリスト
        bone_name_mapping: 標準化されたボーン名からオリジナルボーン名へのマッピング辞書
    """
    armature_rig: bpy.types.Armature = rig_object.data

    with ModeContext.editing(rig_object):
        for metarig_bone_name, vrm_bone_name in bone_mapping:
            # 目のボーンは特別処理（ORGプレフィックスを使用）
            if metarig_bone_name in ["eye.L", "eye.R"]:
                rig_bone = armature_rig.edit_bones[f"ORG-{metarig_bone_name}"]
                rig_bone.use_deform = True
            else:
                # 変形用ボーン（DEFプレフィックス）を使用
                rig_bone = armature_rig.edit_bones[f"DEF-{metarig_bone_name}"]
                assert rig_bone.use_deform

            # オリジナルのボーン名が存在する場合はそれを使用
            target_name = vrm_bone_name
            if bone_name_mapping and vrm_bone_name in bone_name_mapping:
                target_name = bone_name_mapping[vrm_bone_name]

            print(f"renaming bone '{get_full_bone_path(rig_bone)}' to '{target_name}'")
            rig_bone.name = target_name

        # Special handling: if a bone exactly matches "root", rename it to "Root"
        for bone in armature_rig.edit_bones:
            if bone.name == "root":
                bone.name = "Root"
                break


def attach_unmapped_vrm_model_bones_to_rig(
        rig_object: bpy.types.Object, vrm_object: bpy.types.Object, bone_name_mapping=None):
    """
    マッピングされていないVRMモデルのボーンをRigifyリグに追加する関数
    
    Args:
        rig_object: Rigifyリグオブジェクト
        vrm_object: VRMモデルのアーマチュアオブジェクト
        bone_name_mapping: 標準化されたボーン名からオリジナルボーン名へのマッピング辞書
    """
    armature_rig: bpy.types.Armature = rig_object.data
    armature_vrm: bpy.types.Armature = vrm_object.data
    
    # 逆方向のマッピングを作成（オリジナル名 → 標準化名）
    reverse_mapping = {}
    if bone_name_mapping:
        for std_name, orig_name in bone_name_mapping.items():
            reverse_mapping[orig_name] = std_name
    
    with ModeContext.editing(rig_object):
        for vrm_bone in armature_vrm.bones:
            # vrm_boneの名前を取得（標準化後の名前）
            vrm_bone_name = vrm_bone.name
            
            # リグでの名前を確認（標準化前の名前で比較）
            original_name = bone_name_mapping.get(vrm_bone_name, vrm_bone_name) if bone_name_mapping else vrm_bone_name
            bone_already_in_rig = original_name in armature_rig.edit_bones
            
            vrm_bone_has_parent = bool(vrm_bone.parent)
            if bone_already_in_rig or not vrm_bone_has_parent:
                continue
                
            # 親ボーンの名前も処理
            vrm_parent_name = vrm_bone.parent.name
            parent_original_name = bone_name_mapping.get(vrm_parent_name, vrm_parent_name) if bone_name_mapping else vrm_parent_name
            
            parent_exists_in_rig = parent_original_name in armature_rig.edit_bones
            if not parent_exists_in_rig:
                continue
                
            # 親ボーンをリグで取得
            parent_bone_in_rig = armature_rig.edit_bones[parent_original_name]
            print(f"generating bone '{get_full_bone_path(parent_bone_in_rig)}/{original_name}'")
            
            # ボーン名を決定（オリジナル名を使用）
            bone_in_rig = armature_rig.edit_bones.new(original_name)
            bone_in_rig.head = vrm_bone.head_local
            bone_in_rig.tail = vrm_bone.tail_local
            bone_in_rig.parent = parent_bone_in_rig
            
            # Blenderバージョンによる処理分岐
            if blender_version() <= 3:
                print('Blender version is less than 3')
                bone_in_rig.layers = parent_bone_in_rig.layers
                continue
            if blender_version() >= 4:
                pass
            # Blender 4以降ではコレクションにボーンを追加
            for collection in parent_bone_in_rig.collections:
                collection.assign(bone_in_rig)

#endregion

#################################################
#region VRMモデルの特殊機能とRigifyリグの連携関数
#################################################

def copy_shape_key_controls_from_vrm_armature(
        rig_object: bpy.types.Object, vrm_object: bpy.types.Object):
    """
    VRMモデルのシェイプキー制御（表情など）をRigifyリグにコピーする関数
    
    Args:
        rig_object: Rigifyリグオブジェクト
        vrm_object: VRMモデルのアーマチュアオブジェクト
    """
    armature_rig: bpy.types.Armature = rig_object.data
    armature_vrm: bpy.types.Armature = vrm_object.data

    # VRM0のブレンドシェイプマスター（表情制御）をコピー
    blend_shape_master = armature_vrm.vrm_addon_extension.vrm0["blend_shape_master"]
    armature_rig.vrm_addon_extension.vrm0["blend_shape_master"] = blend_shape_master
    
    # VRM1の表情情報をコピー
    expressions = armature_vrm.vrm_addon_extension.vrm1["expressions"]
    armature_rig.vrm_addon_extension.vrm1["expressions"] = expressions


def  modify_rigify_rig_eyes_control_bones(rig_object):
    """
    Rigifyリグの目制御ボーンを調整する関数
    目の位置と動きを自然にするための調整
    
    Args:
        rig_object: Rigifyリグオブジェクト
    """
    obj = bpy.context.object

    with ModeContext.editing(rig_object):
        # 目のマスターコントロールと左目のボーンの位置を取得
        for rig_bone in rig_object.data.edit_bones:
            if rig_bone.name == "master_eye.L":
                m_head_x1, m_head_y1, m_head_z1 = obj.matrix_world @ rig_bone.head
                m_tail_x2, m_tail_y2, m_tail_z2 = obj.matrix_world @ rig_bone.tail
                continue

            if rig_bone.name == "eye.L":
                e_head_x3, e_head_y3, head_z3 = obj.matrix_world @ rig_bone.head
                e_head_length = rig_bone.length
                continue

        # X軸方向の位置計算（傾き計算、分母が0の場合は例外処理）
        x_a = ((m_tail_y2-m_head_y1) / (m_tail_x2-m_head_x1) 
                if m_tail_x2 - m_head_x1 != 0 else 0)
        x_b = m_head_y1 - x_a * m_head_x1
        x_position = (e_head_y3-x_b) / x_a if x_a != 0 else m_head_x1

        # Z軸方向の位置計算
        z_a = ((m_tail_y2-m_head_y1) / (m_tail_z2-m_head_z1) 
                if m_tail_z2 - m_head_z1 != 0 else 0)
        z_b = m_head_y1 - z_a * m_head_z1
        z_position = (e_head_y3-z_b) / z_a if z_a != 0 else m_head_z1

        # スケール比率の計算
        scale_ratio = (x_position-e_head_x3) / e_head_x3

        # 左右の目ボーンの位置調整
        for rig_bone in rig_object.data.edit_bones:
            if rig_bone.name == "eye.L":
                rig_bone.head.x = x_position
                rig_bone.head.z = z_position
                rig_bone.tail.x = x_position
                rig_bone.tail.z = z_position + e_head_length
                continue

            if rig_bone.name == "eye.R":
                rig_bone.head.x = -x_position  # 右目は左目の反転位置
                rig_bone.head.z =  z_position
                rig_bone.tail.x = -x_position
                rig_bone.tail.z =  z_position + e_head_length
                continue
            
        # 目全体のコントロールボーンの調整（計算可能な場合のみ）
        if x_a != 0: 
            for rig_bone in rig_object.data.edit_bones:
                if rig_bone.name == "eyes":
                    rig_bone.head.z = z_position
                    rig_bone.tail.z = z_position + e_head_length
                    rig_bone.length = rig_bone.length * scale_ratio * 1.35
                    break

#endregion

#################################################
#region リグの最終調整と表示設定の関数
#################################################

def disable_ik_stretching(rig_object: bpy.types.Object):
    """
    IK（インバースキネマティクス）のストレッチ機能を無効にする関数
    より自然なポージングのために調整
    
    Args:
        rig_object: Rigifyリグオブジェクト
    """
    stretch_key = "IK_Stretch"
    for bone in rig_object.pose.bones:
        if stretch_key in bone:
            bone[stretch_key] = 0.0


def show_ik_toggle_pole(rig_object: bpy.types.Object):
    """
    IKポールベクトルトグルを表示する関数
    IKコントロールの可視性と選択可能性を調整
    
    Args:
        rig_object: Rigifyリグオブジェクト
    """
    name_LRs = ['.L','.R']  # 左右識別子

    chk_bone_name = "upper_arm_parent"   # 上腕親ボーン名
    toggle_pole_key = "pole_vector"      # ポールベクトル設定キー

    target_bone_name = "upper_arm_ik_target"  # IKターゲットボーン名

    # 選択するボーン名を収集
    bones_to_select = []

    # 左右の腕のIKポールベクトルを表示
    for name_LR in name_LRs:
        if rig_object.pose.bones[chk_bone_name + name_LR][toggle_pole_key] == False:
            rig_object.pose.bones[chk_bone_name + name_LR][toggle_pole_key] = True
            bones_to_select.append(target_bone_name + name_LR)
            rig_object.pose.bones[target_bone_name + name_LR].bone.hide = False

    # ボーン選択（バージョン分岐）
    # Blender 5.0でBone.selectが削除されたため、バージョンによって処理を分ける
    if bones_to_select:
        if blender_version() >= 5:
            # Blender 5.0以降: Edit Modeでedit_bonesを使って選択
            current_mode = bpy.context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            for bone_name in bones_to_select:
                if bone_name in rig_object.data.edit_bones:
                    rig_object.data.edit_bones[bone_name].select = True
            bpy.ops.object.mode_set(mode=current_mode)
        else:
            # Blender 4.x: 従来通りbone.selectを使用
            for bone_name in bones_to_select:
                rig_object.pose.bones[bone_name].bone.select = True


def update_vertex_groups_to_original_names(mesh_object, bone_name_mapping):
    """
    メッシュの頂点グループ名をオリジナルのボーン名に更新する関数

    Args:
        mesh_object: 更新するメッシュオブジェクト
        bone_name_mapping: 標準化されたボーン名からオリジナルボーン名へのマッピング辞書
    """
    if bone_name_mapping is None:
        return

    # 名前の衝突を避けるため、元の名前とハッシュ値を記録
    temp_mapping = {}  # {一時的な名前: (元の標準化名, ターゲット名)}

    # 頂点グループのリネーム（一時的な名前を使用して衝突を避ける）
    for vg in mesh_object.vertex_groups:
        if vg.name in bone_name_mapping:
            # 64文字制限を考慮した短い一時名を生成（ハッシュ値を使用）
            temp_name = f"_TMP_{hash(vg.name) % 1000000:06d}"
            temp_mapping[temp_name] = (vg.name, bone_name_mapping[vg.name])
            vg.name = temp_name

    # 一時的な名前からオリジナルの名前に変更
    for vg in mesh_object.vertex_groups:
        if vg.name in temp_mapping:
            _, target_name = temp_mapping[vg.name]
            vg.name = target_name


def copy_meshes_between_armatures(vrm_object, rig_object, bone_name_mapping=None):
    """
    VRMモデルのメッシュをRigifyリグにコピーする関数
    
    Args:
        vrm_object: VRMモデルのアーマチュアオブジェクト
        rig_object: Rigifyリグオブジェクト
        bone_name_mapping: 標準化されたボーン名からオリジナルボーン名へのマッピング辞書
    """
    # VRMモデルの子メッシュオブジェクトをすべてコピー
    for vrm_child in vrm_object.children:
        if vrm_child.type == 'MESH':
            new_mesh = vrm_child.copy()
            
            # 新しいメッシュをコレクションに追加
            bpy.context.collection.objects.link(new_mesh)
            
            # 頂点グループ名をオリジナルのボーン名に更新
            update_vertex_groups_to_original_names(new_mesh, bone_name_mapping)
            
            # 新しいメッシュをRigifyリグの子に設定
            new_mesh.parent = rig_object
            bpy.ops.object.parent_set(type='ARMATURE', keep_transform=True)


def change_meshes_modifier_object(rig_object):
    """
    メッシュのアーマチュアモディファイアの対象オブジェクトを変更する関数
    
    Args:
        rig_object: Rigifyリグオブジェクト（新しい対象）
    """
    # Rigifyリグの子メッシュのモディファイアを調整
    for rig_child in rig_object.children:
        if rig_child.type == 'MESH':
            for modifier in rig_child.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.object = bpy.data.objects.get(rig_object.name)


def adjust_bone_hierarchy_and_constraints_for_Unity(rig_object):
    """
    Unity向けにRigifyモデルのボーン階層と制約を調整する関数
    
    Args:
        rig_object: Rigifyリグオブジェクト
    """
    armature_data = rig_object.data
    if not isinstance(armature_data, bpy.types.Armature):
        return

    with ModeContext.editing(rig_object):
        # 親子関係の調整
        parent_adjustments = {
            "J_Bip_R_Shoulder": "J_Bip_C_UpperChest",
            "J_Bip_L_Shoulder": "J_Bip_C_UpperChest",
            "J_Bip_L_UpperArm": "J_Bip_L_Shoulder",
            "J_Bip_R_UpperArm": "J_Bip_R_Shoulder",
            "J_Bip_R_UpperLeg": "J_Bip_C_Hips",
            "J_Bip_L_UpperLeg": "J_Bip_C_Hips",
        }

        fingers_dict = {
            'R': ["Thumb1", "Index1", "Middle1", "Ring1", "Little1"],
            'L': ["Thumb1", "Index1", "Middle1", "Ring1", "Little1"]
        }

        # 手の指ボーンの親子関係調整
        for side, fingers in fingers_dict.items():
            for finger in fingers:
                bone_name = f"J_Bip_{side}_{finger}"
                parent_adjustments[bone_name] = f"J_Bip_{side}_Hand"

        # 親子関係の設定
        for bone_name, parent_name in parent_adjustments.items():
            if bone_name in armature_data.edit_bones and parent_name in armature_data.edit_bones:
                armature_data.edit_bones[bone_name].parent = armature_data.edit_bones[parent_name]

        # 目のボーンの調整
        eye_bone_adjustments = {
            "J_Adj_L_FaceEye": {"parent": "J_Bip_C_Head", "target": "MCH-eye.L"},
            "J_Adj_R_FaceEye": {"parent": "J_Bip_C_Head", "target": "MCH-eye.R"}
        }

        for bone_name, adjustment in eye_bone_adjustments.items():
            if bone_name not in armature_data.edit_bones:
                continue

            # 親の設定
            if adjustment['parent'] in armature_data.edit_bones:
                armature_data.edit_bones[bone_name].parent = armature_data.edit_bones[adjustment['parent']]

    # ボーンコレクションと制約の設定（ポーズモードで行う）
    bpy.ops.object.mode_set(mode='POSE')
    
    for bone_name, adjustment in eye_bone_adjustments.items():
        pose_bone = rig_object.pose.bones.get(bone_name)
        if not pose_bone:
            continue

        # DEFコレクションに追加
        for collection in rig_object.data.collections:
            if collection.name == "DEF":
                collection.assign(rig_object.data.bones[bone_name])
                break

        # トランスフォームコピー制約の追加
        target_bone = adjustment['target']
        if target_bone in rig_object.pose.bones:
            constraint = pose_bone.constraints.new('COPY_TRANSFORMS')
            constraint.target = rig_object
            constraint.subtarget = target_bone

    bpy.ops.object.mode_set(mode='OBJECT')

#endregion

#################################################
#region ドライバのセットアップ
#################################################
def setup_rig_constraint_drivers(rig_object):
    """
    Set up constraint influence drivers for a Rigify rig.
    
    Args:
        rig_object: The Rigify rig object
        
    Returns:
        bool: True if drivers were added successfully
    """
    if rig_object.type != 'ARMATURE':
        print("Object is not an armature. Cannot set up constraint drivers.")
        return False
        
    # Add the custom property for global influence control if it doesn't exist
    if 'constraint_influence' not in rig_object:
        rig_object['constraint_influence'] = 1.0
        # Add property metadata for UI
        try:
            ui_data = rig_object.id_properties_ui('constraint_influence')
            ui_data.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, 
                           description="Global influence of DEF bone constraints")
        except (AttributeError, TypeError):
            # Older Blender versions have different API
            pass
    
    # Add drivers to all constraints in DEF bone collection
    result = constraint_driver_utils.add_constraint_influence_drivers(rig_object)
    
    print(f"Added constraint drivers to {len(result)} bones in {rig_object.name}")
    return bool(result)

#endregion

#################################################
#region Debug
#################################################
def debug_bone_name_mapping(original_bone_names, bone_name_mapping, vrm_object):
    """
    bone_name_mappingの内容を詳細に検証するデバッグ関数
    
    Args:
        original_bone_names: 標準化前のオリジナルボーン名の辞書
        bone_name_mapping: 標準化後のボーン名からオリジナルボーン名へのマッピング辞書
        vrm_object: VRMモデルのアーマチュアオブジェクト
    """
    print("\n==== BONE NAME MAPPING DEBUG ====")
    
    # 1. オリジナルボーン名の一覧を表示
    print("\n[Original Bone Names before standardization]")
    for i, (bone_name, original_name) in enumerate(original_bone_names.items()):
        print(f"{i}: {bone_name} -> {original_name}")
    
    # 2. 標準化後のアーマチュアのボーン一覧を表示
    print("\n[Current Armature Bones after standardization]")
    for i, bone in enumerate(vrm_object.data.bones):
        print(f"{i}: {bone.name}")
    
    # 3. 作成されたマッピングの内容を表示
    print("\n[Generated Bone Name Mapping]")
    if bone_name_mapping:
        for i, (std_name, orig_name) in enumerate(bone_name_mapping.items()):
            print(f"{i}: {std_name} -> {orig_name}")
    else:
        print("Warning: bone_name_mapping is empty or None!")
    
    # 4. VRM規定外ボーンの検出
    print("\n[Custom/Non-Standard VRM Bones Check]")
    custom_bone_keywords = ["bust", "breast", "chest", "tail", "hair", "skirt", "sleeve"]
    
    # オリジナルボーン名から探す
    print("In original bones:")
    found_custom_bones = []
    for bone_name in original_bone_names.keys():
        for keyword in custom_bone_keywords:
            if keyword.lower() in bone_name.lower():
                print(f"Found potential custom bone: {bone_name}")
                found_custom_bones.append(bone_name)
                break
    
    # 現在のアーマチュアから探す
    print("\nIn current armature:")
    for bone in vrm_object.data.bones:
        for keyword in custom_bone_keywords:
            if keyword.lower() in bone.name.lower() and bone.name not in found_custom_bones:
                print(f"Found potential custom bone: {bone.name}")
                break
    
    # 5. マッピングに含まれているか確認
    print("\n[Custom Bones in Mapping]")
    for bone_name in found_custom_bones:
        # 標準化後のボーン名を探す
        standardized_name = None
        for std_name, orig_name in bone_name_mapping.items():
            if orig_name == bone_name:
                standardized_name = std_name
                break
        
        if standardized_name:
            print(f"Custom bone '{bone_name}' is mapped as '{standardized_name}'")
        else:
            print(f"Warning: Custom bone '{bone_name}' is NOT in the mapping!")
    
    print("\n==== END OF BONE NAME MAPPING DEBUG ====\n")


def debug_attach_unmapped_bones(rig_object, vrm_object, bone_name_mapping):
    """
    非マッピングボーンのアタッチ処理をデバッグする関数
    
    Args:
        rig_object: Rigifyリグオブジェクト
        vrm_object: VRMモデルのアーマチュアオブジェクト
        bone_name_mapping: 標準化されたボーン名からオリジナルボーン名へのマッピング辞書
    """
    print("\n==== ATTACH UNMAPPED BONES DEBUG ====")
    
    armature_rig = rig_object.data
    armature_vrm = vrm_object.data
    
    # 1. VRMの全ボーン一覧
    print("\n[All VRM Bones]")
    vrm_bone_names = [bone.name for bone in armature_vrm.bones]
    for i, bone_name in enumerate(vrm_bone_names):
        parent_name = armature_vrm.bones[bone_name].parent.name if armature_vrm.bones[bone_name].parent else "None"
        print(f"{i}: {bone_name} (Parent: {parent_name})")
    
    # 2. 既にリグに含まれているボーン
    print("\n[Bones Already in Rig]")
    rig_bone_names = [bone.name for bone in armature_rig.bones]
    for i, bone_name in enumerate(rig_bone_names):
        print(f"{i}: {bone_name}")
    
    # 3. アタッチ候補となるボーン
    print("\n[Potential Bones to Attach]")
    for vrm_bone in armature_vrm.bones:
        bone_already_in_rig = vrm_bone.name in rig_bone_names
        vrm_bone_has_parent = bool(vrm_bone.parent)
        
        if bone_already_in_rig:
            print(f"Skip - Already in rig: {vrm_bone.name}")
            continue
        if not vrm_bone_has_parent:
            print(f"Skip - No parent: {vrm_bone.name}")
            continue
            
        vrm_bone_parent_name = vrm_bone.parent.name
        parent_exists_in_rig = vrm_bone_parent_name in rig_bone_names
        
        if not parent_exists_in_rig:
            print(f"Skip - Parent not in rig: {vrm_bone.name} (Parent: {vrm_bone_parent_name})")
            continue
            
        # マッピングを適用するかどうかの決定
        bone_name = vrm_bone.name
        mapped_name = None
        if bone_name_mapping and bone_name in bone_name_mapping:
            mapped_name = bone_name_mapping[bone_name]
            print(f"Will attach: {vrm_bone.name} -> {mapped_name} (Parent: {vrm_bone_parent_name})")
        else:
            print(f"Will attach: {vrm_bone.name} (No mapping) (Parent: {vrm_bone_parent_name})")
    
    # 4. 特定のカスタムボーン（Bustなど）を詳細に確認
    print("\n[Custom Bones Detailed Check]")
    custom_bone_keywords = ["bust", "breast", "chest", "tail", "hair", "skirt", "sleeve"]
    
    for keyword in custom_bone_keywords:
        for vrm_bone in armature_vrm.bones:
            if keyword.lower() in vrm_bone.name.lower():
                bone_already_in_rig = vrm_bone.name in rig_bone_names
                vrm_bone_has_parent = bool(vrm_bone.parent)
                parent_name = vrm_bone.parent.name if vrm_bone_has_parent else "None"
                parent_exists_in_rig = parent_name in rig_bone_names if vrm_bone_has_parent else False
                
                print(f"Custom bone: {vrm_bone.name}")
                print(f"  - Already in rig: {bone_already_in_rig}")
                print(f"  - Has parent: {vrm_bone_has_parent} ({parent_name})")
                print(f"  - Parent in rig: {parent_exists_in_rig}")
                
                if bone_name_mapping and vrm_bone.name in bone_name_mapping:
                    print(f"  - Mapped to: {bone_name_mapping[vrm_bone.name]}")
                else:
                    print(f"  - Not in mapping")
                    
    print("\n==== END OF ATTACH UNMAPPED BONES DEBUG ====\n")


