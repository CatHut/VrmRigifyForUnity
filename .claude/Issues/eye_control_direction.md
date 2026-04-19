# Issue: eyes デフォルト位置での瞳の向きずれ

## ブランチ
`update_00001`（mainブランチにもデバッグログを移植済み）

## 症状
`eyes` ボーンをデフォルト位置に置いた状態で、瞳が正面を向かない（下方向を向く）。

---

## 調査で判明した事実

### ボーン座標値（不具合モデル）
```
eye.L local head Y:    -0.2572  （VRM LeftEye ボーンの位置 = 顔の表面）
MCH-eye.L head Y:      -0.0187  （眼球根本、顔の内側）
MCH-eye.L tail Y:      -0.0187  （head と同じ、Z方向のみ長さがある）
MCH-eye.L length:       0.0146
master_eye.L head Y:   -0.0187  （MCH-eye.L と同じ）
master_eye.L tail Y:   -0.0187  （head と同じ、長さゼロ）
eyes デフォルト Y:     -0.2572  （VRM目の表面位置のまま）
```

### 正常モデルとの比較
| | 正常モデル | 不具合モデル |
|---|---|---|
| eye.L Y | -0.0925 | -0.2572 |
| MCH-eye.L Y | -0.0046 | -0.0187 |
| eye.L Y - MCH Y | -0.0879（前方） | -0.2385（後方） |

### 根本原因
`position_metarig_bones_to_vrm_model` でメタリグの `eye.L` を VRM の `LeftEye` ボーン位置（顔表面 Y=-0.2572）に合わせるため、Rigify 生成後の `eyes` / `eye.L` もその Y を引き継ぐ。

`MCH-eye.L` の `Damped Track` は「MCH-eye.L から eye.L の方向を向く」ため、`eye.L` が `MCH-eye.L` より後方（Y大）にあると後ろを向く → 結果として下方向になる。

### 試みた対処
`modify_rigify_rig_eyes_control_bones` で `eye.L`/`eye.R`/`eyes` の Y を
`eye_front_y = controller_y - eye_length`（= -0.0187 - 0.0146 = -0.0333）に設定、
`use_connect=False` で独立させた。

結果：`eyes after Y = -0.0437` と意図通りに変化したが、見た目はほぼ変わらず。

---

## 未解決の疑問点

1. `eyes after Y = -0.0437` は `MCH-eye.L Y = -0.0187` より前方のはずだが、なぜ効果がないか
   - `use_connect=False` にしても `eyes` の親子関係で `eye.L` が別の影響を受けている可能性
   - `MCH-eyes_parent` の `COPY_TRANSFORMS → ORG-face` が上書きしている可能性
   - ポーズモードでの実際の位置を確認していない（Edit mode の値のみ確認）

2. `LeftEye_end` の存在
   - 不具合モデルは `LeftEye_end` が `ORG` コレクションに存在する
   - 正常モデル（`J_Adj_L_FaceEye`）には `_end` ボーンがない
   - これが何らかの影響を与えているか未確認

3. コレクションの違い
   - 正常: `J_Adj_L_FaceEye` → `['ORG', 'DEF']`
   - 不具合: `LeftEye` → `['ORG']` のみ
   - `DEF` コレクションに入っていないことの影響未確認

---

## 現在のコードの状態（mainブランチ）

### `modify_rigify_rig_eyes_control_bones`（vrm_rigify.py:788付近）
- `eye_front_y = controller_y - eye_length` で前方Y位置を計算
- `eye.L`/`eye.R`/`eyes` の head/tail Y を `eye_front_y` に設定
- `use_connect=False` で独立させている

### デバッグログ（mainブランチに移植済み）
- `[eye pos debug]` → `modify_rigify_rig_eyes_control_bones` 内の座標ログ
- `[eye mapping debug]` → bone_mapping の eye エントリ確認
- `==== [eye constraints debug] ====` → 目関連ボーンのコンストレイント一覧
- `==== [shape key drivers debug] ====` → シェイプキードライバ一覧
- ログファイルは `.blend` と同じディレクトリに `vrm_rigify_YYYYMMDD_HHMMSS.log` として出力

---

## 次に試すべきアプローチ（未実施）

1. **ポーズモードで実際の `eye.L` 位置を確認する**
   - Edit mode の座標と pose mode での実際位置が一致しているか
   - `MCH-eyes_parent` の `COPY_TRANSFORMS` による影響を確認

2. **`Damped Track` の track_axis を確認・変更する**
   - 現在どの軸を使って追跡しているか未確認
   - `-Y` 軸方向に追跡している場合、eye.L が前方にあっても軸の向きで正面にならない可能性

3. **メタリグ段階で `eye.L` の Y 位置を VRM ボーンに合わせないようにする**
   - `position_metarig_bones_to_vrm_model` で eye ボーンのみ Y を変更しない
   - Rigify 生成後の `eyes` デフォルト Y を保持する

4. **`LeftEye_end` の削除を試みる**
   - `removed_rigify_rig_facial_bones` または後処理で `_end` ボーンを削除

---

## 関連ファイル
- `vrm_rigify_for_unity/vrm_rigify.py`
- `vrm_rigify_for_unity/__init__.py`
- `.claude/Task/handover_eye_control.md`（初期のハンドオーバー資料）
