# ハンドオーバー資料：目のコントロール修正

## ブランチ
`update_00001`

## 背景
Spineボーン数対応の変更（`update_00001`）を行ったところ、自作VRMモデルで目のコントロール（`eyes` ボーン）が機能しなくなった。mainブランチ・別モデルでは正常動作していた。

---

## 解決済みの問題

### 1. `__init__.py` の呼び出し引数不足（解決済み）
`adjust_bone_hierarchy_and_constraints_for_Unity` に `bone_mapping` / `bone_name_mapping` が渡されていなかった。

### 2. 目ボーンのコンストレイント未設定（解決済み）
旧コードは `J_Adj_L_FaceEye` / `J_Adj_R_FaceEye` というボーン名をハードコードしていた。このボーンを持たないモデルでは目のコンストレイント（`COPY_TRANSFORMS` → `MCH-eye.L`）が設定されなかった。

**修正内容：** `bone_mapping` からVRM Humanoidの `eye.L` / `eye.R` に対応するボーン名を動的に解決し、コンストレイントを設定するよう変更。

### 3. 親子関係調整のボーン名ハードコード（解決済み）
`J_Bip_*` ボーン名のハードコードを廃止し、VRM Humanoidボーン名（`rightShoulder` など）から `bone_name_mapping` 経由で実際のボーン名に解決するよう変更。

### 4. `use_connect` が外れて `eyes` と `eye.L` の接続が切れる問題（解決済み）
`modify_rigify_rig_eyes_control_bones` で `eye.L` / `eye.R` の head/tail を書き換えると `use_connect` が外れ、`eyes` コントロールとの親子接続が切れる。`use_connect = True` を再設定して解決。

---

## 未解決の問題：`eyes` デフォルト位置での瞳の向きずれ

### 症状
`eyes` ボーンをY=0（デフォルト）に置いた状態で、瞳が下方を向いてしまう。

### 構造（Rigify標準）
```
eyes (コントロール, Faceコレクション)
  └─ eye.L (子ボーン, use_connect=True, Faceコレクション)
       ↑ Damped Track で参照
MCH-eye.L (眼球根本, MCHコレクション)
  └─ LeftEye (COPY_TRANSFORMS ← MCH-eye.L, ORGコレクション)
```

`MCH-eye.L` の `Damped Track` が `eye.L` を追跡し、`eye.L` の位置によって眼球の向きが決まる。

### 判明している座標値（このモデルの場合）
```
eye.L local head:   (0.0398, -0.2572, 1.0110)  ← VRMモデルの目の表面位置
MCH-eye.L head y:   -0.0187                    ← 眼球根本（顔の内部）
master_eye.L head y: -0.0187
```

### 問題の核心
`eye.L` は `eyes` の子で `use_connect=True` のため、`eyes` の tail 位置 = `eye.L` の head 位置になる。

現状の `eyes` の配置：
- Y = `-0.2572`（`eye.L` のローカルY = VRMの目の表面）
- これは `MCH-eye.L`（Y=-0.0187）より後ろ（Yが大きい＝顔の内側方向）

`Damped Track` は「`MCH-eye.L` から `eye.L` の方向を向く」ので、`eye.L` が `MCH-eye.L` より後ろにあると後ろを向く → 結果として下方向になっている。

### 試みた対処と問題点
1. `eyes` のY位置を `master_eye.L`（Y=-0.0187）に設定 → `use_connect=True` により `eye.L` も Y=-0.0187 に吸着 → `MCH-eye.L` と同位置になり `Damped Track` が不定方向になる
2. `eye.L` のY位置のみ変更せず X/Z のみ調整 → `eyes` の tail（= `eye.L` の head）が `eyes` の Y 位置に従うため結局同じ問題

### 根本的な疑問
`use_connect=True` の状態で `eyes` を動かすと `eye.L` は常に `eyes` の延長線上にある。このとき `MCH-eye.L` の `Damped Track` は `eye.L` の絶対位置（= `eyes` の tail 位置）を参照するので、`eyes` のデフォルトY位置が `MCH-eye.L` より前方（Yマイナス）にあれば正面を向くはず。

→ `eyes` のデフォルトY位置を `MCH-eye.L` より前方（例：Y=-0.0187 より小さい値）にすれば解決するはず。

### 次に試すべきこと
`eyes` のY位置（head.y / tail.y）を直接 `MCH-eye.L` のY座標（-0.0187）に設定する。ただし `use_connect=True` により `eye.L` も同じY位置に吸着するため、`eye.L` と `MCH-eye.L` のY差がなくなる問題が再発する懸念がある。

**可能性のある解決策：**
- `eye.L` の `use_connect` を `False` にして、`eye.L` の絶対位置を `MCH-eye.L` より前方に手動配置する
- `eyes` の配置はそのままにして、`MCH-eye.L` の `Damped Track` の軸設定（`track_axis`）を調整する
- Rigify生成直後（位置調整前）の `eyes` の Y 座標を取得して利用する

---

## 現在のコードの状態

### `modify_rigify_rig_eyes_control_bones`（vrm_rigify.py:786）
- 旧コードのワールド座標計算（ワールド/ローカル混在バグあり）を廃止
- `eye.L` のローカル座標から X/Z を取得し調整
- `use_connect = True` を設定（これが問題）
- `eyes` の Z位置を `eye.L` と合わせ、Y位置は Rigify 生成値のまま

### デバッグ用関数（未整理、後で削除が必要）
- `debug_eye_constraints(rig_object)` → 目関連ボーンのコンストレイント一覧
- `debug_shape_key_drivers(rig_object)` → シェイプキードライバ一覧
- `[eye pos debug]` プリント文 → 座標確認用

---

## 関連ファイル
- `vrm_rigify_for_unity/vrm_rigify.py`
- `vrm_rigify_for_unity/__init__.py`
