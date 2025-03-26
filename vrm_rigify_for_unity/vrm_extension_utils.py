def copy_vrm_extension_from_armature(vrm_object, rig_object):
    """
    VRMモデルのアーマチュアからVRM拡張情報をRigifyリグにコピーする関数
    ※この関数は、メッシュのコピーとアーマチュアモディファイアの更新が完了した後に呼び出すこと
    
    Args:
        vrm_object: VRMモデルのアーマチュアオブジェクト（コピー元）
        rig_object: Rigifyリグオブジェクト（コピー先）
    """
    import bpy
    from mathutils import Matrix, Vector
    
    # アーマチュアデータを取得
    armature_vrm = vrm_object.data
    armature_rig = rig_object.data
    
    # デバッグ出力
    print(f"Copying VRM extension from {vrm_object.name} to {rig_object.name}")
    
    # vrm_addon_extensionが存在するか確認
    if not hasattr(armature_vrm, "vrm_addon_extension") or not hasattr(armature_rig, "vrm_addon_extension"):
        print("Error: vrm_addon_extension not found on one of the armatures")
        return

    # spec_versionを保存（VRM 0.0またはVRM 1.0）
    spec_version = armature_vrm.vrm_addon_extension.spec_version
    
    # =====================================================
    # 1. VRM0の情報をコピー
    # =====================================================
    # VRM0のプロパティをコピー（メタ情報、ヒューマノイド設定など）
    try:
        # メタ情報のコピー
        armature_rig.vrm_addon_extension.vrm0.meta.author = armature_vrm.vrm_addon_extension.vrm0.meta.author
        armature_rig.vrm_addon_extension.vrm0.meta.version = armature_vrm.vrm_addon_extension.vrm0.meta.version
        armature_rig.vrm_addon_extension.vrm0.meta.title = armature_vrm.vrm_addon_extension.vrm0.meta.title
        armature_rig.vrm_addon_extension.vrm0.meta.contact_information = armature_vrm.vrm_addon_extension.vrm0.meta.contact_information
        armature_rig.vrm_addon_extension.vrm0.meta.reference = armature_vrm.vrm_addon_extension.vrm0.meta.reference
        armature_rig.vrm_addon_extension.vrm0.meta.allowed_user_name = armature_vrm.vrm_addon_extension.vrm0.meta.allowed_user_name
        armature_rig.vrm_addon_extension.vrm0.meta.violent_ussage_name = armature_vrm.vrm_addon_extension.vrm0.meta.violent_ussage_name
        armature_rig.vrm_addon_extension.vrm0.meta.sexual_ussage_name = armature_vrm.vrm_addon_extension.vrm0.meta.sexual_ussage_name
        armature_rig.vrm_addon_extension.vrm0.meta.commercial_ussage_name = armature_vrm.vrm_addon_extension.vrm0.meta.commercial_ussage_name
        armature_rig.vrm_addon_extension.vrm0.meta.license_name = armature_vrm.vrm_addon_extension.vrm0.meta.license_name
        armature_rig.vrm_addon_extension.vrm0.meta.other_license_url = armature_vrm.vrm_addon_extension.vrm0.meta.other_license_url
        
        # サムネイル画像のコピー
        if armature_vrm.vrm_addon_extension.vrm0.meta.texture:
            armature_rig.vrm_addon_extension.vrm0.meta.texture = armature_vrm.vrm_addon_extension.vrm0.meta.texture
            
        # ブレンドシェイプマスターのコピー（既存のコードでも実装されている）
        blend_shape_master = armature_vrm.vrm_addon_extension.vrm0["blend_shape_master"]
        armature_rig.vrm_addon_extension.vrm0["blend_shape_master"] = blend_shape_master
    except Exception as e:
        print(f"Error while copying VRM0 meta info: {e}")
        
    # ボーンマッピング情報を更新
    try:
        # VRM0のヒューマノイド設定のコピーと更新
        # 既にボーン名と階層が一致しているので、直接マッピングを行う
        for human_bone in armature_vrm.vrm_addon_extension.vrm0.humanoid.human_bones:
            if human_bone.node.bone_name:
                original_bone = human_bone.node.bone_name
                # 同じ名前のボーンがRigifyリグに存在するか確認
                if original_bone in armature_rig.bones:
                    new_human_bone = next((hb for hb in armature_rig.vrm_addon_extension.vrm0.humanoid.human_bones if hb.bone == human_bone.bone), None)
                    if new_human_bone:
                        new_human_bone.node.bone_name = original_bone
        
    except Exception as e:
        print(f"Error while updating VRM0 bone mapping: {e}")

    # SpringBoneの設定をコピー
    try:
        # VRM0のセカンダリアニメーション（SpringBone）設定
        secondary_animation_src = armature_vrm.vrm_addon_extension.vrm0.secondary_animation
        secondary_animation_dst = armature_rig.vrm_addon_extension.vrm0.secondary_animation
        
        # ボーングループのコピー
        secondary_animation_dst.bone_groups.clear()
        for bone_group in secondary_animation_src.bone_groups:
            new_group = secondary_animation_dst.bone_groups.add()
            new_group.comment = bone_group.comment
            new_group.stiffiness = bone_group.stiffiness  # 注：typoですがVRM0の仕様通り
            new_group.gravity_power = bone_group.gravity_power
            new_group.gravity_dir = bone_group.gravity_dir
            new_group.drag_force = bone_group.drag_force
            new_group.hit_radius = bone_group.hit_radius
            
            # 中心ボーンの設定
            if bone_group.center.bone_name:
                new_group.center.bone_name = bone_group.center.bone_name
            
            # ボーンリストのコピー
            for bone in bone_group.bones:
                if bone.bone_name:
                    new_bone = new_group.bones.add()
                    new_bone.bone_name = bone.bone_name
            
            # コライダーグループのコピー
            for collider_group in bone_group.collider_groups:
                new_collider_group = new_group.collider_groups.add()
                new_collider_group.value = collider_group.value
        
        # コライダーグループのコピー
        secondary_animation_dst.collider_groups.clear()
        for collider_group in secondary_animation_src.collider_groups:
            new_group = secondary_animation_dst.collider_groups.add()
            new_group.node.bone_name = collider_group.node.bone_name
            new_group.uuid = collider_group.uuid
            
            # コライダーのコピー
            for collider in collider_group.colliders:
                if collider.bpy_object:
                    # コライダーオブジェクトの複製
                    new_collider_obj = collider.bpy_object.copy()
                    bpy.context.collection.objects.link(new_collider_obj)
                    new_collider_obj.parent = rig_object
                    
                    # 新しいコライダーに追加
                    new_collider = new_group.colliders.add()
                    new_collider.bpy_object = new_collider_obj
                    
    except Exception as e:
        print(f"Error while copying SpringBone settings: {e}")
        
    # =====================================================
    # 2. VRM1の情報をコピー
    # =====================================================
    try:
        # メタ情報のコピー
        vrm1_meta_src = armature_vrm.vrm_addon_extension.vrm1.meta
        vrm1_meta_dst = armature_rig.vrm_addon_extension.vrm1.meta
        
        # 基本情報をコピー
        vrm1_meta_dst.vrm_name = vrm1_meta_src.vrm_name
        vrm1_meta_dst.version = vrm1_meta_src.version
        vrm1_meta_dst.copyright_information = vrm1_meta_src.copyright_information
        vrm1_meta_dst.contact_information = vrm1_meta_src.contact_information
        vrm1_meta_dst.third_party_licenses = vrm1_meta_src.third_party_licenses
        vrm1_meta_dst.avatar_permission = vrm1_meta_src.avatar_permission
        vrm1_meta_dst.allow_excessively_violent_usage = vrm1_meta_src.allow_excessively_violent_usage
        vrm1_meta_dst.allow_excessively_sexual_usage = vrm1_meta_src.allow_excessively_sexual_usage
        vrm1_meta_dst.commercial_usage = vrm1_meta_src.commercial_usage
        vrm1_meta_dst.allow_political_or_religious_usage = vrm1_meta_src.allow_political_or_religious_usage
        vrm1_meta_dst.allow_antisocial_or_hate_usage = vrm1_meta_src.allow_antisocial_or_hate_usage
        vrm1_meta_dst.credit_notation = vrm1_meta_src.credit_notation
        vrm1_meta_dst.allow_redistribution = vrm1_meta_src.allow_redistribution
        vrm1_meta_dst.modification = vrm1_meta_src.modification
        vrm1_meta_dst.other_license_url = vrm1_meta_src.other_license_url
        
        # サムネイル画像のコピー
        if vrm1_meta_src.thumbnail_image:
            vrm1_meta_dst.thumbnail_image = vrm1_meta_src.thumbnail_image
            
        # 作者情報のコピー
        vrm1_meta_dst.authors.clear()
        for author in vrm1_meta_src.authors:
            new_author = vrm1_meta_dst.authors.add()
            new_author.value = author.value
            
        # 参照情報のコピー
        vrm1_meta_dst.references.clear()
        for reference in vrm1_meta_src.references:
            new_reference = vrm1_meta_dst.references.add()
            new_reference.value = reference.value
    except Exception as e:
        print(f"Error while copying VRM1 meta info: {e}")
        
    # VRM1のボーンマッピングを更新
    try:
        # VRM1のヒューマノイドボーン設定
        human_bones_src = armature_vrm.vrm_addon_extension.vrm1.humanoid.human_bones
        human_bones_dst = armature_rig.vrm_addon_extension.vrm1.humanoid.human_bones
        
        # ヒューマノイドの人体ボーン定義をコピーと更新
        human_bone_name_to_human_bone_src = human_bones_src.human_bone_name_to_human_bone()
        human_bone_name_to_human_bone_dst = human_bones_dst.human_bone_name_to_human_bone()
        
        for bone_name, human_bone_src in human_bone_name_to_human_bone_src.items():
            if human_bone_src.node.bone_name:
                original_bone = human_bone_src.node.bone_name
                human_bone_dst = human_bone_name_to_human_bone_dst.get(bone_name)
                
                # 同じ名前のボーンがRigifyリグに存在するか確認
                if human_bone_dst and original_bone in armature_rig.bones:
                    human_bone_dst.node.bone_name = original_bone
    except Exception as e:
        print(f"Error while updating VRM1 bone mapping: {e}")
    
    # Expressions（表情）のコピー
    try:
        # 既存の実装と類似
        expressions = armature_vrm.vrm_addon_extension.vrm1["expressions"]
        armature_rig.vrm_addon_extension.vrm1["expressions"] = expressions
        
        # 表情内のメッシュ参照を更新（マテリアルバインディング、モーフターゲットバインディングなど）
        # メッシュオブジェクトのマッピングを作成
        mesh_object_mapping = {}
        for vrm_child in vrm_object.children:
            if vrm_child.type == 'MESH':
                for rig_child in rig_object.children:
                    if rig_child.type == 'MESH' and rig_child.data.name == vrm_child.data.name:
                        mesh_object_mapping[vrm_child.name] = rig_child.name
                        break
        
        # 表情内のメッシュ参照を更新
        expressions_dst = armature_rig.vrm_addon_extension.vrm1.expressions
        
        # メッシュオブジェクトのマッピングがない場合は、現在の状態から作成
        if not mesh_object_mapping:
            for vrm_child in vrm_object.children:
                if vrm_child.type == 'MESH':
                    for rig_child in rig_object.children:
                        if (rig_child.type == 'MESH' and 
                            rig_child.data.name == vrm_child.data.name):
                            mesh_object_mapping[vrm_child.name] = rig_child.name
                            print(f"Mapped mesh: {vrm_child.name} → {rig_child.name}")
                            break
                            
        # すべての表情（プリセットとカスタム）を更新
        # プリセット表情の処理
        preset_expressions = expressions_dst.preset
        for preset_name in dir(preset_expressions):
            if preset_name.startswith('__') or not hasattr(preset_expressions, preset_name):
                continue
                
            preset_expr = getattr(preset_expressions, preset_name)
            if hasattr(preset_expr, 'morph_target_binds'):
                # モーフターゲットバインドの更新
                for morph_bind in preset_expr.morph_target_binds:
                    old_mesh_name = morph_bind.node.mesh_object_name
                    if old_mesh_name in mesh_object_mapping:
                        morph_bind.node.mesh_object_name = mesh_object_mapping[old_mesh_name]
                        print(f"Updated mesh reference in preset '{preset_name}': {old_mesh_name} → {mesh_object_mapping[old_mesh_name]}")
        
        # カスタム表情の処理
        for custom_expr in expressions_dst.custom:
            # モーフターゲットバインドの更新
            for morph_bind in custom_expr.morph_target_binds:
                old_mesh_name = morph_bind.node.mesh_object_name
                if old_mesh_name in mesh_object_mapping:
                    morph_bind.node.mesh_object_name = mesh_object_mapping[old_mesh_name]
                    print(f"Updated mesh reference in custom expression: {old_mesh_name} → {mesh_object_mapping[old_mesh_name]}")
    except Exception as e:
        print(f"Error while copying expressions: {e}")
    
    # Look Atの設定をコピー
    try:
        look_at_src = armature_vrm.vrm_addon_extension.vrm1.look_at
        look_at_dst = armature_rig.vrm_addon_extension.vrm1.look_at
        
        # 基本設定のコピー
        look_at_dst.offset_from_head_bone = look_at_src.offset_from_head_bone
        look_at_dst.type = look_at_src.type
        
        # 範囲マップの設定をコピー
        look_at_dst.range_map_horizontal_inner.input_max_value = look_at_src.range_map_horizontal_inner.input_max_value
        look_at_dst.range_map_horizontal_inner.output_scale = look_at_src.range_map_horizontal_inner.output_scale
        
        look_at_dst.range_map_horizontal_outer.input_max_value = look_at_src.range_map_horizontal_outer.input_max_value
        look_at_dst.range_map_horizontal_outer.output_scale = look_at_src.range_map_horizontal_outer.output_scale
        
        look_at_dst.range_map_vertical_down.input_max_value = look_at_src.range_map_vertical_down.input_max_value
        look_at_dst.range_map_vertical_down.output_scale = look_at_src.range_map_vertical_down.output_scale
        
        look_at_dst.range_map_vertical_up.input_max_value = look_at_src.range_map_vertical_up.input_max_value
        look_at_dst.range_map_vertical_up.output_scale = look_at_src.range_map_vertical_up.output_scale
    except Exception as e:
        print(f"Error while copying look_at settings: {e}")
    
    # First Person（一人称視点）の設定をコピー
    try:
        first_person_src = armature_vrm.vrm_addon_extension.vrm1.first_person
        first_person_dst = armature_rig.vrm_addon_extension.vrm1.first_person
        
        # メッシュアノテーション情報をクリア、コピー
        first_person_dst.mesh_annotations.clear()
        
        for mesh_annotation in first_person_src.mesh_annotations:
            if mesh_annotation.node.mesh_object_name in mesh_object_mapping:
                new_annotation = first_person_dst.mesh_annotations.add()
                new_annotation.type = mesh_annotation.type
                new_annotation.node.mesh_object_name = mesh_object_mapping[mesh_annotation.node.mesh_object_name]
    except Exception as e:
        print(f"Error while copying first person settings: {e}")

    # VRM1のSpringBone設定をコピー
    try:
        # VRM1のSpringBone情報の取得
        spring_bone1_src = armature_vrm.vrm_addon_extension.spring_bone1
        spring_bone1_dst = armature_rig.vrm_addon_extension.spring_bone1
        
        # コライダーのコピー
        spring_bone1_dst.colliders.clear()
        for collider in spring_bone1_src.colliders:
            new_collider = spring_bone1_dst.colliders.add()
            new_collider.name = collider.name
            new_collider.uuid = collider.uuid
            
            # ノード（ボーン）情報のコピー
            if collider.node.bone_name:
                new_collider.node.bone_name = collider.node.bone_name
            
            # シェイプ情報のコピー
            new_collider.shape_type = collider.shape_type
            
            if collider.shape_type == collider.SHAPE_TYPE_SPHERE.identifier:
                new_collider.shape.sphere.fallback_radius = collider.shape.sphere.fallback_radius
                new_collider.shape.sphere.fallback_offset = collider.shape.sphere.fallback_offset
            elif collider.shape_type == collider.SHAPE_TYPE_CAPSULE.identifier:
                new_collider.shape.capsule.fallback_radius = collider.shape.capsule.fallback_radius
                new_collider.shape.capsule.fallback_offset = collider.shape.capsule.fallback_offset
                new_collider.shape.capsule.fallback_tail = collider.shape.capsule.fallback_tail
            
            # 拡張情報のコピー（VRMC_springBone_extended_collider）
            ext_src = collider.extensions.vrmc_spring_bone_extended_collider
            ext_dst = new_collider.extensions.vrmc_spring_bone_extended_collider
            
            ext_dst.enabled = ext_src.enabled
            ext_dst.automatic_fallback_generation = ext_src.automatic_fallback_generation
            ext_dst.shape_type = ext_src.shape_type

        # コライダーオブジェクトの視覚的表現を作成
        for new_collider in spring_bone1_dst.colliders:
            # 元のコライダーを探す
            src_collider = None
            for collider in spring_bone1_src.colliders:
                if collider.uuid == new_collider.uuid:
                    src_collider = collider
                    break
            
            # 元のコライダーが見つかった場合
            if src_collider and src_collider.bpy_object:
                # 新しいBPYオブジェクトを作成・設定
                new_collider.reset_bpy_object(bpy.context, rig_object)
                
                if new_collider.bpy_object:
                    # サイズをコピー
                    new_collider.bpy_object.empty_display_size = src_collider.bpy_object.empty_display_size
                    
                    # 位置と回転をコピー
                    if new_collider.shape_type == new_collider.SHAPE_TYPE_SPHERE.identifier:
                        # 球体の場合、位置をコピー
                        new_collider.shape.sphere.set_offset(src_collider.shape.sphere.offset)
                    elif new_collider.shape_type == new_collider.SHAPE_TYPE_CAPSULE.identifier:
                        # カプセルの場合、両端の位置をコピー
                        new_collider.shape.capsule.set_offset(src_collider.shape.capsule.offset)
                        new_collider.shape.capsule.set_tail(src_collider.shape.capsule.tail)
                        
                        # 子オブジェクト（tail）のサイズをコピー
                        if new_collider.bpy_object.children and src_collider.bpy_object.children:
                            new_collider.bpy_object.children[0].empty_display_size = src_collider.bpy_object.children[0].empty_display_size
            else:
                # 元のコライダーが見つからない場合は単純に作成
                new_collider.reset_bpy_object(bpy.context, rig_object)
            
        # コライダーグループのコピー
        spring_bone1_dst.collider_groups.clear()
        for collider_group in spring_bone1_src.collider_groups:
            new_group = spring_bone1_dst.collider_groups.add()
            new_group.vrm_name = collider_group.vrm_name
            new_group.name = collider_group.name
            new_group.uuid = collider_group.uuid
            
            # コライダー参照のコピー
            for collider_ref in collider_group.colliders:
                new_ref = new_group.colliders.add()
                new_ref.collider_name = collider_ref.collider_name
                new_ref.collider_uuid = collider_ref.collider_uuid
        
        # スプリングのコピー
        spring_bone1_dst.springs.clear()
        for spring in spring_bone1_src.springs:
            new_spring = spring_bone1_dst.springs.add()
            new_spring.vrm_name = spring.vrm_name
            
            # 中心ボーン情報のコピー
            if spring.center.bone_name:
                new_spring.center.bone_name = spring.center.bone_name
            
            # ジョイント（ボーン）情報のコピー
            for joint in spring.joints:
                new_joint = new_spring.joints.add()
                if joint.node.bone_name:
                    new_joint.node.bone_name = joint.node.bone_name
                new_joint.hit_radius = joint.hit_radius
                new_joint.stiffness = joint.stiffness
                new_joint.gravity_power = joint.gravity_power
                new_joint.gravity_dir = joint.gravity_dir
                new_joint.drag_force = joint.drag_force
            
            # コライダーグループ参照のコピー
            for collider_group_ref in spring.collider_groups:
                new_ref = new_spring.collider_groups.add()
                new_ref.collider_group_name = collider_group_ref.collider_group_name
                new_ref.collider_group_uuid = collider_group_ref.collider_group_uuid
        
        # アニメーション設定のコピー
        spring_bone1_dst.enable_animation = spring_bone1_src.enable_animation
        
        print(f"VRM1 SpringBone settings copied successfully")
    except Exception as e:
        print(f"Error while copying VRM1 SpringBone settings: {e}")
    
    # VRM0とVRM1の情報をコピーした後、バージョン設定を更新
    armature_rig.vrm_addon_extension.spec_version = spec_version
    
    print(f"VRM extension copied from {vrm_object.name} to {rig_object.name}")
    return True
