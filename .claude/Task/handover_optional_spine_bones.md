# ハンドオーバー: VRMオプション脊椎ボーン対応

## 目的
VRMのオプションボーン（upperChest / neck / chest）が存在しないモデルで
`GenerateRigifyFromVRM` を実行するとエラーになる問題への対応。

---

## 問題の背景

### VRM脊椎ボーンの構成
VRM仕様では以下が**必須**、残りは**オプション**：
- 必須: hips, spine, head
- オプション: chest, upperChest, neck

### Rigifyメタリグの脊椎ボーン名（標準）
```
spine      → hips       (必須)
spine.001  → spine      (必須)
spine.002  → chest      (オプション)
spine.003  → upperChest (オプション)
spine.004  → neck       (オプション)
spine.005  → (Rigify内部: head の直接親、VRMには対応なし)
spine.006  → head       (必須)
```

### 元々のエラー
`upperChest` がないモデルで `DEF-spine.006` が見つからないエラー：
```
Error: 'bpy_prop_collection[key]: key "DEF-spine.006" not found'
```

---

## 現在の修正状況（未完了）

### 変更ファイル
- `vrm_rigify_for_unity/vrm_rigify.py`
- `vrm_rigify_for_unity/__init__.py`

### 変更の概要

#### 1. `remove_or_log_unmapped_metarig_bones`（第1段階）
位置合わせ**前**に呼ぶ。palm / pelvis / breast のみ削除。
spine.* の削除はここでは行わない（位置合わせに影響するため）。

#### 2. `remove_unmapped_spine_bones`（第2段階・新規追加）
位置合わせ**後**、Rigify生成**前**に呼ぶ。
未マッピングの `spine.*` を削除し、削除前に子ボーンの親を
直近のマッピード祖先に付け替える。

#### 3. `adjust_position_of_metarig_spine_bones`
`spine.004` 決め打ちをやめ、`bone_mapping` の spine エントリ末尾から
neck相当ボーンを動的に特定するよう変更。引数に `bone_mapping` を追加。

#### 4. `__init__.py` のフロー変更
```python
bone_mapping = remove_or_log_unmapped_metarig_bones(metarig, bone_mapping)  # 第1段階
position_metarig_bones_to_vrm_model(...)                                     # 位置合わせ
adjust_position_of_metarig_spine_bones(metarig, bone_mapping)                # spine調整
...（その他の調整）...
remove_unmapped_spine_bones(metarig, bone_mapping)                           # 第2段階
generate_rigify_rig(metarig)                                                  # Rigify生成
```

---

## 現在発生しているエラー

```
RIGIFY ERROR: Bone 'spine.004': Cannot connect chain - bone position is disjoint.
```

### 原因分析
`remove_unmapped_spine_bones` で `spine.003`（upperChest相当）を削除する際、
子の `spine.004`（neck）の親を `spine.002`（chest）に付け替えているが、
`spine.004` の `head` 位置が `spine.002` の `tail` 位置と一致していないため
Rigify が "disjoint" と判定してエラーになる。

Rigify の spine チェーンは `use_connect = True` によって各ボーンの head が
親の tail と同一位置であることを要求する。
`spine.003` を削除して `spine.004` の親を `spine.002` に変えても、
`spine.004.head` は VRM の neck の head_local に合わせられており、
`spine.002.tail`（= VRM の chest の tail_local）と位置が異なる。

### 解決の方向性

**案A（推奨）: `use_connect` を利用して位置を強制的に合わせる**
`spine.004` の親を `spine.002` に付け替えた後、
`spine.004.use_connect = True` にすることで head 位置を親の tail に
スナップさせ、その後 `use_connect = False` に戻す。
ただし、これだと neck の head 位置が chest の tail 位置に強制されるため
VRMモデルの neck 位置とずれる可能性がある。
VRM では neck の head は chest（または spine）の tail と同一位置であるはずなので
実用上は問題ないと思われる。

**案B: spine.003 を削除せず、tail 位置を spine.004 の head に合わせる**
`spine.003` を削除する代わりに、tail を `spine.004.head` と同一にすることで
長さ0（または極小）のボーンとしてチェーンを維持する。
Rigify が長さ0のボーンをどう扱うか要確認。

**案C: 削除対象 spine.* の tail を次のマッピードボーンの head に合わせてから削除**
削除前に `spine.003.tail = spine.004.head` を設定し、
その後 `spine.004.use_connect = True → False` でスナップ。

**現時点での推奨は案A**。実装は `remove_unmapped_spine_bones` 内で
親付け替え後に `use_connect` の ON/OFF を追加するだけ。

---

## 次のスレッドでやること

1. `remove_unmapped_spine_bones` の親付け替え処理に以下を追加：
   ```python
   for child in list(metarig_bone.children):
       child.parent = new_parent
       # 親の tail に head をスナップして接続を保証
       if re.match(r"^spine(\.\d+)?$", child.name):
           child.use_connect = True
           child.use_connect = False
   ```
2. 標準的なVRMサンプルモデルで動作確認（リグレッション確認）
3. upperChest なしモデルで動作確認

---

## デバッグ出力について
`rename_rig_bones_to_match_vrm_model_vertex_groups` に追加した
`print` 文はデバッグ用で、修正完了後に削除すること。
（現在は `print(f"renaming bone ...")` が残っている）
