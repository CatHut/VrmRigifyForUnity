# ハンドオーバー: VRMオプション脊椎ボーン対応（続き）

## 目的
VRMのオプションボーン（upperChest / neck / chest）が存在しないモデルで
`GenerateRigifyFromVRM` を実行するとエラーになる問題への対応。

前回ハンドオーバー資料: `handover_optional_spine_bones.md`

---

## 前回からの変更内容

### 1. `remove_unmapped_spine_bones`（vrm_rigify.py）
- 未マッピングの spine.* を削除（親付け替え + `use_connect` スナップ）
- 削除後に残った spine チェーンを `spine` / `spine.001` / `spine.002` ... と連番に振り直す
- `bone_mapping` の spine エントリも新連番名に更新して返す（戻り値あり）
- **理由**: Rigify は実際に存在する spine ボーンの数に合わせて DEF ボーンを連番生成するため、
  削除後の連番と bone_mapping を一致させる必要がある

### 2. `rename_rig_bones_to_match_vrm_model_vertex_groups`（vrm_rigify.py）
- spine チェーン末尾（head 相当）を特定し、`ORG-spine.XXX` を使用 + `use_deform = True` に設定
- **理由**: Rigify の spine チェーンの最終ボーン（head）には `DEF-` が生成されず `ORG-` のみ存在する

### 3. `attach_unmapped_vrm_model_bones_to_rig`（vrm_rigify.py）
- 1パスのループを「未追加ボーンがなくなるまで繰り返す」方式に変更
- **理由**: 1パスでは同じループ内で追加した親ボーンを次の反復で「親として」認識できず、
  複数階層のカスタムボーンが追加されない問題があった

### 4. `__init__.py`
- `bone_mapping = vrm_rigify.remove_unmapped_spine_bones(metarig, bone_mapping)` と
  戻り値を受け取るよう変更
- ログ出力機能を追加（Blendファイルと同じフォルダに `vrm_rigify_YYYYMMDD_HHMMSS.log`）

---

## 現在の状況

### 解決済み
- `DEF-spine.006 not found` エラー → 連番振り直し + ORG フォールバックで解決
- カスタムボーン（Hair, Tail 等）が1階層しか追加されない問題 → 繰り返しループで解決

### 未解決: 生成リグのボーン構造が不完全

#### 症状
Blender のアウトライナーで確認すると、生成されたリグのボーン階層が以下のような状態：
```
Root
  Hips
    Spine
      Chest
        Neck        ← Head がない、腕・脚・指も見当たらない
    Ribbon_root
    Tail
```

#### ログ上は正常
ログ（`vrm_rigify_20260411_111354.log`）では全ボーンが正常に生成・リネームされている：
- `renaming bone '...DEF-spine.003' to 'Neck'`
- `renaming bone '...ORG-spine.004' to 'Head'` ← 正常
- 腕・脚・指のリネームも全て成功
- `generating bone` でカスタムボーンも全階層生成済み

#### 推測される原因
ログ上は成功しているが Blender UI に反映されていないことから、以下が疑われる：

**仮説A: `ORG-spine.004`（Head）の `use_deform = True` 設定が問題**
`ORG-spine.004` は Rigify の内部ボーンであり、`use_deform = True` にすることで
Rigify の内部コンストレイント/ドライバーが壊れ、その子孫（Head 配下の全ボーン、
および ORG-spine.003 配下の腕・脚）が正しく表示されない可能性がある。

**仮説B: `adjust_bone_hierarchy_and_constraints_for_Unity` での処理**
リネーム後に呼ばれるこの関数が、予期しないボーンを削除・移動している可能性。

**仮説C: アウトライナーのフィルター/コレクション表示の問題**
ボーン自体は存在するが、非表示コレクションに分類されている可能性。
（ただしユーザーは「ヒエラルキー上ではすべて表示されるはず」と確認済み）

---

## 次のスレッドでやること

### 優先度1: 原因の特定

#### 仮説Aの検証
`rename_rig_bones_to_match_vrm_model_vertex_groups` で Head（spine チェーン末尾）の
処理を変更し、`use_deform = True` を設定しないパターンで試す。
ただし `use_deform` なしでは頂点グループへの影響が出ないため、
別の方法（DEF ボーンを新規追加して Head の位置にコピーする等）が必要かもしれない。

#### 仮説Bの検証
`adjust_bone_hierarchy_and_constraints_for_Unity` の処理内容を確認する。
この関数でボーンが削除・再配置されていないか確認。

```python
# __init__.py 上の呼び出し順序
vrm_rigify.rename_rig_bones_to_match_vrm_model_vertex_groups(...)  # リネーム
vrm_rigify.attach_unmapped_vrm_model_bones_to_rig(...)              # カスタムボーン追加
...
vrm_rigify.adjust_bone_hierarchy_and_constraints_for_Unity(rig_object)  # ← ここが怪しい？
```

#### 仮説Cの検証
Blender の編集モードに入ってボーンが実際に存在するか確認してもらう。

### 優先度2: デバッグ出力の整理（修正完了後）
以下のデバッグ用 `print` 文を削除すること：
- `vrm_rigify.py` の `rename_rig_bones_to_match_vrm_model_vertex_groups` 内の
  spine デバッグブロック（`==== DEBUG: spine-related bones in rig ====`）
- `vrm_rigify.py` の `rename_rig_bones_to_match_vrm_model_vertex_groups` 内の
  `print(f"renaming bone ...")` 行
- `__init__.py` のログ出力機能は残しても良い（デバッグに有用）

### 優先度3: リグレッション確認（修正完了後）
- **標準VRMモデル**（hips / spine / chest / upperChest / neck / head すべてあり）で動作確認
- **upperChest なしモデル**（今回の対象）で動作確認

---

## 現在のコード構造メモ

### spine チェーンの対応表（upperChest なしモデルの場合）

| メタリグ削除前 | VRM対応  | 削除? | 削除後の連番 | Rigify DEF/ORG |
|--------------|---------|------|------------|----------------|
| spine        | hips    | No   | spine      | DEF-spine      |
| spine.001    | spine   | No   | spine.001  | DEF-spine.001  |
| spine.002    | chest   | No   | spine.002  | DEF-spine.002  |
| spine.003    | upperChest | **Yes** | (削除) | -           |
| spine.004    | neck    | No   | spine.003  | DEF-spine.003  |
| spine.005    | (内部)  | **Yes** | (削除) | -            |
| spine.006    | head    | No   | spine.004  | **ORG-spine.004**（DEFなし）|

### ログファイルについて
実行ログは Blendファイルと同じフォルダに `vrm_rigify_YYYYMMDD_HHMMSS.log` として出力される。
未保存の場合は `~/tmp/` に出力。

---

## 参考: 関連ログファイル
- `vrm_rigify_20260411_105722.log` - DEF-spine.004 not found エラー時
- `vrm_rigify_20260411_105941.log` - ORG フォールバック実装後（Head リネーム成功）
- `vrm_rigify_20260411_111354.log` - 繰り返しループ実装後（ログ上は全成功、UI上でボーン欠損）
