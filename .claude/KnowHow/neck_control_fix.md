# upperChestなしVRMモデルでNeckコントロールが生成されない問題の修正

## 問題の概要

upperChest ボーンを持たない VRM モデル（Hips / Spine / Chest / Neck / Head の5本構成）に
対してツールを実行すると、生成された Rigify リグに `neck` コントロールボーンが存在せず、
Neck の位置に Head 操作用コントロールが配置されてしまう問題。

## 原因の調査過程

### 1. neck_count パラメータは存在しない

最初は `spine` ポーズボーンの `rigify_parameters.neck_count` を設定しようとしたが、
Rigify 5.0 のパラメータ名は `neck_pos` であり `neck_count` は存在しない。

### 2. neck_pos の設定は効果がなかった

`neck_pos = 4` を正しく設定しても neck コントロールが生成されない。

Rigify の `super_spine` は内部で `connected_children_names()` を使ってスパインチェーンを
収集するが、この関数は **`use_connect=True` のボーンしか辿らない**。

VRM モデルのボーン位置を `position_metarig_bones_to_vrm_model()` で設定する際に
`edit_bone.head` / `edit_bone.tail` を直接書き換えると、Blender が自動的に
`use_connect` を `False` にする。

そのため `spine.003`（Neck）と `spine.004`（Head）の `use_connect` が `False` になり、
`super_spine` の `orgs` リストには `[spine, spine.001, spine.002]` の3本しか含まれなかった。

### 3. テンプレートメタリグはすでに basic_spine + super_head 構成

Rigify の human メタリグテンプレートは `spine` ボーンに `spines.basic_spine`、
`spine.003`（neck相当）に `spines.super_head` が割り当てられている。

`super_head` も同様に `connected_children_names()` でチェーンを辿るため、
`spine.004`（Head）の `use_connect=False` が問題の本質だった。

`super_head` の `has_neck` は `len(self.bones.org) > 1` で決まる。
`spine.004` が `use_connect=False` のため `orgs = [spine.003]` の1本になり
`has_neck=False` → neck コントロールが生成されなかった。

## 修正内容

### 修正箇所

`vrm_rigify.py` の `set_metarig_spine_neck_pos()` 関数（`__init__.py` から
`remove_unmapped_spine_bones()` の直後に呼び出される）。

### 修正方針

Neck より後（Head 以降）のボーンを `use_connect=True` に戻し、
`use_connect=True` によって head が親の tail にスナップされるため
VRM の位置から `tail` を再設定する。

Neck 自体（spine.003）は `basic_spine` チェーンから切り離すため `use_connect=False` のまま。

```python
def set_metarig_spine_neck_pos(metarig, bone_mapping, vrm_object=None):
    # spine エントリから Neck のインデックスを取得
    neck_idx = ...  # vb.lower() == "neck" のインデックス

    # Neck より後（Head以降）を use_connect=True に修正
    with ModeContext.editing(metarig):
        for i in range(neck_idx + 1, len(spine_entries)):
            bone.use_connect = True
            bone.tail = armature_vrm.bones[vb].tail_local  # tail を再設定
```

### spine_tail_bone の特殊扱いを廃止

従来は `rename_rig_bones_to_match_vrm_model_vertex_groups()` で spine チェーン末尾（Head）に
`DEF-` ボーンが生成されないため `ORG-` を使う特殊処理があった。

`use_connect=True` にすることで `super_head` が Head に対しても `DEF-` ボーンを生成するため、
この特殊処理は不要になり削除した。

## 呼び出し順序

```
remove_unmapped_spine_bones(metarig, bone_mapping)  # spine チェーン確定
set_metarig_spine_neck_pos(metarig, bone_mapping, vrm_object)  # use_connect 修正
generate_rigify_rig(metarig)  # Rigify 生成
```

## 検証結果

修正後のログ（constraint drivers 出力）：
```
Neck: 1 constraint drivers added.
Head: 1 constraint drivers added.
```

Neck と Head が別々のコントロールボーンとして正しく生成されることを確認。
