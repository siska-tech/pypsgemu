# オプションD: core.tick() 見直し - 詳細修正案

作成日: 2025-10-03
対象: pypsgemu v1.0.0

---

## 1. 現状の問題分析

### 1.1 重大な発見

**プリスケーラの二重実装問題**を発見しました：

```python
# tone_generator.py:47-70 - プリスケーラは既に実装済み！
def update(self, cycles: int) -> None:
    for _ in range(cycles):
        self._prescaler_counter += 1

        # プリスケーラ（16分周）
        if self._prescaler_counter >= 16:
            self._prescaler_counter = 0
            self._counter -= 1

            if self._counter <= 0:
                self._output = not self._output
                self._counter = self._period
```

しかし、AY38910Core側では：

```python
# ay38910.py:188-215 - 毎サイクル update(1) を呼んでいる
def _update_generators_inline(self, registers: List[int]) -> None:
    for i in range(NUM_TONE_CHANNELS):
        # ...
        self._tone_generators[i].update(1)  # ← 毎サイクル呼ぶので無駄
```

**問題**:
- ジェネレータ側で16分周しているのに、毎マスタークロックサイクルでupdate(1)を呼んでいる
- 本来16サイクルごとに1回呼べば良いのに、16倍の関数呼び出しコストが発生

### 1.2 パフォーマンスボトルネック（実測ベース）

プロファイリング結果（1102サンプル生成、66.95ms）:

```
Total time: 66.95ms per chunk (1102 samples)
└─ generate_samples() loop: 66.95ms (100%)
    ├─ core.tick() calls: ~50ms (75%)
    │   └─ _tick_batch() loop: ~48ms (96%)
    │       ├─ Pythonループオーバーヘッド: ~30ms (45%)
    │       └─ _update_generators_inline(): ~18ms (27%)
    │           ├─ set_period() 呼び出し: ~6ms (9%)
    │           ├─ update() 呼び出し: ~8ms (12%)
    │           └─ get_output() 呼び出し: ~4ms (6%)
    ├─ core.get_mixed_output(): ~10ms (15%)
    └─ NumPy array operations: ~7ms (10%)
```

**ボトルネックTop 3**:
1. **Pythonループオーバーヘッド** (30ms, 45%)
2. **不要な関数呼び出し** (18ms, 27%) ← プリスケーラ実装で削減可能
3. **get_mixed_output()** (10ms, 15%)

---

## 2. 修正案の全体像

### 2.1 修正方針

**3段階の最適化**:

1. **Phase 1: プリスケーラの適切な実装** (最大効果)
   - マスタークロックカウンタを使ってジェネレータ更新頻度を制御
   - 16分周: トーン/ノイズは16サイクルに1回のみupdate()
   - 256分周: エンベロープは256サイクルに1回のみupdate()
   - **期待効果: 50-70%高速化（2-3倍）**

2. **Phase 2: 関数呼び出しのインライン化** (追加効果)
   - set_period()を毎サイクル呼ばず、レジスタ変更時のみ
   - ジェネレータの内部状態に直接アクセス
   - **期待効果: 追加で20-30%（合計3-4倍）**

3. **Phase 3: get_mixed_output()の最適化** (追加効果)
   - リスト作成を回避
   - ローカル変数にキャッシング
   - **期待効果: 追加で10-15%（合計4-5倍）**

### 2.2 期待される成果

| Phase | リアルタイム倍率 | 改善率 | 実装時間 |
|-------|----------------|-------|---------|
| 現在 | 0.39x | - | - |
| Phase 1 | **0.8-1.2x** | **2.0-3.0倍** | 1日 |
| Phase 2 | **1.2-1.6x** | **3.0-4.0倍** | 1-2日 |
| Phase 3 | **1.6-2.0x** | **4.0-5.0倍** | 0.5日 |

---

## 3. Phase 1: プリスケーラの適切な実装

### 3.1 修正内容

#### 修正ファイル: `pypsgemu/core/ay38910.py`

**現在の実装（問題あり）**:
```python
def _tick_batch(self, master_cycles: int) -> int:
    consumed_cycles = 0
    registers = self._state.registers
    batch_size = min(master_cycles, 64)

    while consumed_cycles < master_cycles:
        remaining = master_cycles - consumed_cycles
        current_batch = min(batch_size, remaining)

        for _ in range(current_batch):
            self._update_generators_inline(registers)  # ← 毎サイクル呼ぶ
            self._state.master_clock_counter += 1

        consumed_cycles += current_batch

    return consumed_cycles

def _update_generators_inline(self, registers: List[int]) -> None:
    # トーン/ノイズ/エンベロープを毎サイクル更新 ← 無駄！
    for i in range(NUM_TONE_CHANNELS):
        fine = registers[i * 2]
        coarse = registers[i * 2 + 1] & 0x0F
        self._tone_generators[i].set_period(fine, coarse)  # ← 毎サイクル呼ぶ必要なし
        self._tone_generators[i].update(1)
        self._state.tone_outputs[i] = self._tone_generators[i].get_output()

    # ノイズとエンベロープも同様...
```

**修正後（Phase 1）**:
```python
def _tick_batch(self, master_cycles: int) -> int:
    """Phase 1最適化: プリスケーラを活用したバッチ実行"""
    consumed_cycles = 0

    # ローカル変数にキャッシュ
    master_clock = self._state.master_clock_counter

    # マスタークロックループ
    for _ in range(master_cycles):
        master_clock += 1

        # トーン/ノイズジェネレータ更新（16分周）
        if (master_clock & 0x0F) == 0:  # master_clock % 16 == 0 の最適化版
            self._update_tone_noise_generators()

        # エンベロープジェネレータ更新（256分周）
        if (master_clock & 0xFF) == 0:  # master_clock % 256 == 0
            self._update_envelope_generator()

        consumed_cycles += 1

    # マスタークロックを書き戻し
    self._state.master_clock_counter = master_clock

    return consumed_cycles

def _update_tone_noise_generators(self) -> None:
    """トーン/ノイズジェネレータ更新（16分周後に1回）"""
    registers = self._state.registers

    # トーンジェネレータ更新（ループ展開）
    # チャンネルA
    self._tone_generators[0].update(1)
    self._state.tone_outputs[0] = self._tone_generators[0].get_output()

    # チャンネルB
    self._tone_generators[1].update(1)
    self._state.tone_outputs[1] = self._tone_generators[1].get_output()

    # チャンネルC
    self._tone_generators[2].update(1)
    self._state.tone_outputs[2] = self._tone_generators[2].get_output()

    # ノイズジェネレータ更新
    self._noise_generator.update(1)
    self._state.noise_output = self._noise_generator.get_output()
    self._state.lfsr_value = self._noise_generator.get_lfsr_state()

def _update_envelope_generator(self) -> None:
    """エンベロープジェネレータ更新（256分周後に1回）"""
    self._envelope_generator.update(1)
    self._state.envelope_level = self._envelope_generator.get_level()
    self._state.envelope_holding = self._envelope_generator.is_holding()
    self._state.envelope_attacking = self._envelope_generator.is_attacking()
```

**変更点の説明**:

1. **マスタークロックベースの制御**
   - `master_clock & 0x0F == 0`でトーン/ノイズ更新（16分周）
   - `master_clock & 0xFF == 0`でエンベロープ更新（256分周）
   - ビット演算は剰余演算より高速

2. **set_period()の削除**
   - 毎サイクル呼ぶのではなく、レジスタ書き込み時のみ実行
   - `write_register()`内の`_handle_register_write()`で対応済み

3. **更新頻度の削減**
   - トーン/ノイズ: 16回に1回のみupdate()（93.75%削減）
   - エンベロープ: 256回に1回のみupdate()（99.6%削減）

### 3.2 レジスタ書き込み時の周期更新

**修正ファイル**: `pypsgemu/core/ay38910.py`

```python
def _handle_register_write(self, address: int, value: int) -> None:
    """レジスタ書き込み後の処理（Phase 1拡張）"""
    # トーン周期レジスタ (R0-R5)
    if 0 <= address <= 5:
        channel = address // 2
        fine = self._state.registers[channel * 2]
        coarse = self._state.registers[channel * 2 + 1] & 0x0F
        self._tone_generators[channel].set_period(fine, coarse)

    # ノイズ周期レジスタ (R6)
    elif address == REG_NOISE_PERIOD:
        noise_period = value & 0x1F
        self._noise_generator.set_period(noise_period)

    # エンベロープ周期レジスタ (R11, R12)
    elif address == REG_ENVELOPE_FINE or address == REG_ENVELOPE_COARSE:
        fine = self._state.registers[REG_ENVELOPE_FINE]
        coarse = self._state.registers[REG_ENVELOPE_COARSE]
        self._envelope_generator.set_period(fine, coarse)

    # エンベロープ形状レジスタ (R13)
    elif address == REG_ENVELOPE_SHAPE:
        shape = value & 0x0F
        self._envelope_generator.set_shape(shape)
        self._state.envelope_level = self._envelope_generator.get_level()
        self._state.envelope_holding = self._envelope_generator.is_holding()
        self._state.envelope_attacking = self._envelope_generator.is_attacking()
```

**変更点**:
- トーン周期レジスタ（R0-R5）の書き込み時にset_period()を呼ぶ
- tick()内では周期設定を行わない

---

## 4. Phase 2: 関数呼び出しのインライン化

### 4.1 修正内容

#### 修正ファイル: `pypsgemu/core/ay38910.py`

**Phase 1のコードをさらに最適化**:

```python
def _tick_batch_phase2(self, master_cycles: int) -> int:
    """Phase 2最適化: 関数呼び出しのインライン化"""
    consumed_cycles = 0

    # ローカル変数に全状態をキャッシュ
    master_clock = self._state.master_clock_counter
    tone_outputs = self._state.tone_outputs

    # ジェネレータの参照をローカル変数化
    tone_gen_0 = self._tone_generators[0]
    tone_gen_1 = self._tone_generators[1]
    tone_gen_2 = self._tone_generators[2]
    noise_gen = self._noise_generator
    env_gen = self._envelope_generator

    # マスタークロックループ
    for _ in range(master_cycles):
        master_clock += 1

        # トーン/ノイズジェネレータ更新（16分周）
        if (master_clock & 0x0F) == 0:
            # update()とget_output()をインライン化
            # トーンA
            tone_gen_0.update(1)
            tone_outputs[0] = tone_gen_0._output  # 直接アクセス（get_output()回避）

            # トーンB
            tone_gen_1.update(1)
            tone_outputs[1] = tone_gen_1._output

            # トーンC
            tone_gen_2.update(1)
            tone_outputs[2] = tone_gen_2._output

            # ノイズ
            noise_gen.update(1)
            self._state.noise_output = noise_gen._output
            self._state.lfsr_value = noise_gen._lfsr.get_value()

        # エンベロープジェネレータ更新（256分周）
        if (master_clock & 0xFF) == 0:
            env_gen.update(1)
            self._state.envelope_level = env_gen._level  # 直接アクセス

        consumed_cycles += 1

    self._state.master_clock_counter = master_clock
    return consumed_cycles
```

**変更点**:
1. `get_output()`を呼ばず、`._output`に直接アクセス
2. ジェネレータの参照をループ外でローカル変数化
3. 属性アクセスの回数を最小化

**注意**: プライベート属性への直接アクセスはカプセル化を破るが、パフォーマンス優先のため許容

---

## 5. Phase 3: get_mixed_output()の最適化

### 5.1 修正内容

#### 修正ファイル: `pypsgemu/core/ay38910.py`

**現在の実装**:
```python
def get_mixed_output(self) -> float:
    mixer_control = self._state.registers[REG_MIXER_CONTROL]

    volume_registers = [
        self._state.registers[REG_VOLUME_A],
        self._state.registers[REG_VOLUME_B],
        self._state.registers[REG_VOLUME_C]
    ]  # ← リスト作成コスト

    output = self._mixer.get_mixed_output(
        self._state.tone_outputs,  # ← リスト渡し
        self._state.noise_output,
        mixer_control,
        volume_registers,
        self._state.envelope_level
    )

    return output * self._config.volume_scale
```

**修正後（Phase 3）**:
```python
def get_mixed_output_optimized(self) -> float:
    """Phase 3最適化: インライン化されたミキシング"""
    # レジスタアクセスを最小化
    registers = self._state.registers
    mixer_control = registers[7]

    # トーン出力（ローカル変数化）
    tone_a = self._state.tone_outputs[0]
    tone_b = self._state.tone_outputs[1]
    tone_c = self._state.tone_outputs[2]
    noise = self._state.noise_output

    # 音量レジスタ
    vol_a = registers[8]
    vol_b = registers[9]
    vol_c = registers[10]

    # エンベロープレベル
    env_level = self._state.envelope_level

    # ボリュームテーブル（ローカル変数化）
    volume_table = self._volume_table._table

    # チャンネルA処理（完全インライン化）
    tone_enable_a = not (mixer_control & 0x01)
    noise_enable_a = not (mixer_control & 0x08)
    output_a = (tone_enable_a and tone_a) or (noise_enable_a and noise)

    if output_a:
        level_a = env_level if (vol_a & 0x10) else (vol_a & 0x0F)
        pcm_a = volume_table[level_a]
    else:
        pcm_a = 0.0

    # チャンネルB処理
    tone_enable_b = not (mixer_control & 0x02)
    noise_enable_b = not (mixer_control & 0x10)
    output_b = (tone_enable_b and tone_b) or (noise_enable_b and noise)

    if output_b:
        level_b = env_level if (vol_b & 0x10) else (vol_b & 0x0F)
        pcm_b = volume_table[level_b]
    else:
        pcm_b = 0.0

    # チャンネルC処理
    tone_enable_c = not (mixer_control & 0x04)
    noise_enable_c = not (mixer_control & 0x20)
    output_c = (tone_enable_c and tone_c) or (noise_enable_c and noise)

    if output_c:
        level_c = env_level if (vol_c & 0x10) else (vol_c & 0x0F)
        pcm_c = volume_table[level_c]
    else:
        pcm_c = 0.0

    # ミックス（3チャンネルの平均）
    mixed = (pcm_a + pcm_b + pcm_c) / 3.0

    # 全体音量スケール
    return mixed * self._config.volume_scale
```

**変更点**:
1. リスト作成を完全に排除
2. Mixerクラスを経由せず直接計算
3. 全てローカル変数でアクセス

### 5.2 既存APIとの互換性

```python
def get_mixed_output(self) -> float:
    """既存API（互換性維持）"""
    # Phase 3が実装されていればそちらを呼ぶ
    if hasattr(self, '_optimized_mixing'):
        return self.get_mixed_output_optimized()
    else:
        # 従来の実装（後方互換性）
        return self._get_mixed_output_legacy()
```

---

## 6. 実装ロードマップ

### Phase 1: プリスケーラ実装（1日）

**タスク**:
- [ ] `_tick_batch()`を修正（マスタークロックベース）
- [ ] `_update_tone_noise_generators()`を実装
- [ ] `_update_envelope_generator()`を実装
- [ ] `_handle_register_write()`を拡張（トーン周期レジスタ対応）
- [ ] ユニットテスト実行
- [ ] パフォーマンス測定（期待: 0.8-1.2x）

### Phase 2: インライン化（1-2日）

**タスク**:
- [ ] `_tick_batch_phase2()`を実装
- [ ] プライベート属性への直接アクセス実装
- [ ] ローカル変数キャッシング最適化
- [ ] ユニットテスト実行
- [ ] パフォーマンス測定（期待: 1.2-1.6x）

### Phase 3: ミキシング最適化（0.5日）

**タスク**:
- [ ] `get_mixed_output_optimized()`を実装
- [ ] 既存APIとの互換性確認
- [ ] ユニットテスト実行
- [ ] パフォーマンス測定（期待: 1.6-2.0x）

### 最終検証（0.5日）

**タスク**:
- [ ] example_audio_test.pyでの動作確認
- [ ] 音質検証（Python版との比較）
- [ ] 全ユニットテスト実行
- [ ] パフォーマンス最終測定
- [ ] ドキュメント更新

**総所要時間**: 3-4日

---

## 7. リスクと対策

### 7.1 技術的リスク

| リスク | 影響度 | 確率 | 対策 |
|-------|--------|------|------|
| プリスケーラ実装で音質変化 | 高 | 低 | 仕様書に準拠、厳密なユニットテスト |
| 直接アクセスでカプセル化破壊 | 中 | 高 | 内部API専用メソッドとして実装 |
| 目標性能に届かない | 中 | 低 | Phase 1で2倍達成見込み |

### 7.2 実装上の注意点

**プリスケーラの正しい実装**:
- マスタークロック2MHz → 16分周でトーン/ノイズクロック125kHz
- これは**仕様書に準拠**した正しい実装
- ジェネレータ側のプリスケーラは既に正しく実装されている

**後方互換性**:
- `get_mixed_output()`は既存APIのまま維持
- 最適化版は`get_mixed_output_optimized()`として実装
- フラグで切り替え可能にする

---

## 8. 成功の評価基準

### 8.1 定量的評価

- [ ] Phase 1完了時: リアルタイム倍率 ≥ 0.8x（2倍高速化）
- [ ] Phase 2完了時: リアルタイム倍率 ≥ 1.2x（3倍高速化）
- [ ] Phase 3完了時: リアルタイム倍率 ≥ 1.5x（4倍高速化）
- [ ] CPU使用率 ≤ 40%
- [ ] アンダーラン率 < 1%

### 8.2 定性的評価

- [ ] 音質が現在のPython版と完全に同じ
- [ ] 仕様書に準拠（16分周/256分周）
- [ ] 全ユニットテストがパス
- [ ] コードの保守性が維持されている

---

## 9. まとめ

### 9.1 修正の核心

**最も重要な修正**:
- ✅ **Phase 1のプリスケーラ実装**が最大の効果（2-3倍）
- ✅ 既存のプリスケーラ実装を活用する正しい設計
- ✅ 仕様書に準拠した実装

### 9.2 期待される成果

| 項目 | 現在 | Phase 1後 | Phase 2後 | Phase 3後 |
|------|------|----------|----------|----------|
| リアルタイム倍率 | 0.39x | 0.8-1.2x | 1.2-1.6x | 1.6-2.0x |
| 改善率 | - | 2-3倍 | 3-4倍 | 4-5倍 |
| 実装期間 | - | 1日 | 2-3日 | 3-4日 |

### 9.3 次のステップ

1. **Phase 1を最優先で実装** → 最大効果（2-3倍）
2. **Phase 1で1.0x達成ならリアルタイム再生可能**
3. 必要に応じてPhase 2-3を追加実装

**推奨**: Phase 1のみ実装して効果測定 → 1.0x達成なら完了
