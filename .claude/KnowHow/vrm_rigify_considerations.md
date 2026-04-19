# VRM に Rigify を適用する際の考慮事項

## VRM ボーン構造の特性

### オプションボーン

VRM1.0 では以下のボーンがオプション（存在しないモデルがある）：

| ボーン | 備考 |
|--------|------|
| upperChest | Chest と Neck の間。存在しないモデルが多い |
| neck | 存在しないモデルは稀だが仕様上オプション |
| eye.L / eye.R | 眼球ボーン |
| toeBase | つま先 |

→ spine チェーンの本数はモデルによって異なる（4〜6本）。
  `remove_unmapped_spine_bones()` で未マッピングの spine.* を削除し
  連番に振り直すことで対応している。

### ボーン名の大文字小文字

Rigify の標準ボーン名（`neck`, `head`, `hips`）はすべて小文字だが、
VRM の標準ボーン名（`bpy.ops.vrm.bones_rename` 後）は PascalCase（`Neck`, `Head`, `Hips`）。

文字列比較は必ず `vb.lower()` などで正規化すること。

### ボーン間の物理的な隙間

VRM モデルのボーンはアニメーション用途のため、Chest の tail と Neck の head が
物理的に離れていることが多い（Rigify テンプレートと異なる）。

`position_metarig_bones_to_vrm_model()` で `edit_bone.head/tail` を書き換えると
Blender が自動的に `use_connect` を `False` にする。

---

## Rigify メタリグの注意事項

### super_spine vs basic_spine + super_head

Rigify の human テンプレートは spine ボーンに `spines.basic_spine`、
neck 相当ボーンに `spines.super_head` が設定されている（`spines.super_spine` ではない）。

`super_spine` は deprecated であり、内部的に `basic_spine` + `super_head` に分解される
互換プロキシである。

### connected_children_names の制約

Rigify が spine/head チェーンを収集する `connected_children_names()` は
**`use_connect=True` のボーンしか辿らない**。

ボーン位置を VRM に合わせた後は以下のボーンの `use_connect` が `False` になりやすい：
- Neck（spine.003 相当）
- Head（spine.004 相当）

`has_neck = len(self.bones.org) > 1`（super_head 内）が `False` になると
neck コントロールボーンが生成されない。

対処：Rigify 生成前に `set_metarig_spine_neck_pos()` で Head の `use_connect` を
`True` に戻し、`tail` を VRM の位置に再設定する。

### rigify_parameters のパラメータ名

| パラメータ | 説明 | デフォルト |
|-----------|------|----------|
| `neck_pos` | Neck 開始位置（1ベース） | 6 |
| `pivot_pos` | torso コントロール位置 | 2 |
| `use_head` | head/neck ボーン生成フラグ | True |
| `segments` | 腕・脚のセグメント数 | 2 |

`neck_count` というパラメータは**存在しない**（混同注意）。

### neck_pos の意味

```python
spine_orgs = orgs[0: neck_pos - 1]  # spine 部分
head_orgs  = orgs[neck_pos - 1:]    # neck/head 部分
```

- 5本チェーン（Hips/Spine/Chest/Neck/Head）で Neck を正しく neck/head に含める場合：
  `neck_pos = 4`（spine.003 が Neck = 4番目）

ただし現在は `basic_spine` + `super_head` の分割構成のため `neck_pos` は使用していない。

### DEF ボーンが生成されるかどうか

| 状況 | DEF ボーン |
|------|-----------|
| super_spine（旧方式）の spine チェーン末尾 | DEF なし、ORG を使用 |
| super_head で use_connect=True の Head | DEF あり |
| super_head で use_connect=False の Head（has_neck=False 時） | 未確認 |

Head に `use_connect=True` を設定した結果 `DEF-spine.004` が生成されるようになったため、
`spine_tail_bone` として `ORG-` を使う特殊処理は不要になった。

---

## デバッグ手法

### ログ出力ポイント

問題調査時に有効だったログ出力箇所：

1. **bone_mapping の内容確認**
   - spine エントリの VRM ボーン名（大文字か小文字か）
   - neck が含まれているかどうか

2. **use_connect の確認**（Rigify 生成直前）
   ```python
   for bone in metarig.data.bones:
       if re.match(r"^spine(\.\d+)?$", bone.name):
           print(f"{bone.name}  use_connect={bone.use_connect}")
   ```

3. **rigify_type と connect_chain の確認**
   ```python
   for pb in metarig.pose.bones:
       if re.match(r"^spine(\.\d+)?$", pb.name) and pb.rigify_type:
           print(f"{pb.name}  rigify_type={pb.rigify_type}")
   ```

4. **生成後のコントロールボーン一覧**
   ```python
   for bone in armature_rig.edit_bones:
       if not re.match(r"^(DEF|ORG|MCH|tweak)-", bone.name):
           print(f"{bone.name}  parent={bone.parent.name if bone.parent else None}")
   ```

5. **constraint drivers の出力**
   - `Neck: N constraint drivers added.` と `Head: N constraint drivers added.` が
     別々に出れば正常

### よくあるエラー

| エラーメッセージ | 原因 | 対処 |
|----------------|------|------|
| `CONFLICT: bone ORG-spine.X is claimed by rigs ...` | basic_spine と super_head が同じボーンを取り合っている。Neck の `use_connect=True` にしたため basic_spine チェーンに含まれた | Neck の `use_connect` は `False` のままにする |
| `Cannot connect chain - bone position is disjoint` | `connect_chain=True` なのにボーンが物理的に離れている | `connect_chain=False` にする、または位置を合わせる |
| `Neck is too short` | `neck_pos >= len(orgs)` | `neck_pos` を小さくする |
| `Neck cannot be below or the same as pivot` | `neck_pos <= pivot_pos` | `neck_pos` を `pivot_pos` より大きくする |

---

## 実装パターン

### spine チェーンの処理順序

```
1. mapping_metarig_and_vrm_model_bones()    # VRM ↔ メタリグ のマッピング生成
2. remove_or_log_unmapped_metarig_bones()   # 非 spine の未マッピングボーン処理
3. position_metarig_bones_to_vrm_model()    # ボーン位置を VRM に合わせる（use_connect が壊れる）
4. adjust_position_of_metarig_spine_bones() # spine 接続位置の微調整
5. remove_unmapped_spine_bones()            # 未マッピングの spine.* を削除して連番振り直し
6. set_metarig_spine_neck_pos()             # use_connect を修正（Head を True に戻す）
7. generate_rigify_rig()                    # Rigify 生成
```

### VRM ボーン名の正規化

`bpy.ops.vrm.bones_rename()` 適用後は PascalCase になる。
比較時は `.lower()` を使うこと。

```python
# NG
if vb == "neck":

# OK
if vb.lower() == "neck":
```
