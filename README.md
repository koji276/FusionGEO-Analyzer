# FusionGEO Analyzer

URLを入力するだけで「AIエージェントに引用される確率」を6+1領域・28項目で自動診断し、改善提案まで出すSaaSツール。BYOK（APIキー持ち込み）+ ラチェット型従量課金モデル。

## Current Status

| Item | Status | Notes |
|------|--------|-------|
| GitHub Repo | ✅ Deployed | `koji276/FusionGEO-Analyzer` (Private) |
| Streamlit Cloud | ✅ Live | クイック解析で実動確認済み |
| GEO Checklist | ✅ 7領域28項目 | D1-D6 + D7 Global Readiness |
| Engine 1 (Static Crawler) | ✅ 稼働中 | 12チェック自動判定（D7-02含む） |
| Engine 2 (LLM Semantic) | ✅ 実装済 | BYOK方式、Trust Graph + Global対応 |
| Engine 3 (Trust/Citation) | 🔧 半自動 | Perplexityプロンプトコピー→ペースト方式 |
| UI (app.py) | ✅ ハイブリッド版 | Plotlyレーダー、st.status、外部データ入力 |
| D7 Global Readiness | ✅ 実装済 | トグルON/OFFで6⇔7角形動的切替 |
| Auto-Fix: llms.txt生成 | ✅ 実装済 | フル解析モードで動作 |
| Auto-Fix: チャンク・リライト | ✅ 実装済 | フル解析モードで動作 |
| **改善提案エンジン** | ⬜ 未実装 | **次の最優先タスク** |

## Architecture

### 3-Engine + Human-in-the-Loop 構成

```
User Input (URL + BYOK API Key)
        │
        ├─► Engine 1: Static Crawler (Rule-Based)
        │     Python (requests + BeautifulSoup)
        │     → robots.txt, llms.txt, セマンティックHTML
        │     → Schema.org, FAQ/HowTo, 鮮度, 画像alt
        │     → D7-02: hreflang/英語リンク/多言語Entity
        │
        ├─► Engine 2: LLM Semantic Analyzer (BYOK)
        │     OpenAI API (ユーザーのキー)
        │     → コンテンツ品質 (D1-04, D3-04, D4-01~03)
        │     → Trust Graph (D1-01~03) ← SNSペーストデータ
        │     → Global Readiness (D7-01, D7-04) ← global_mode時
        │
        └─► Engine 3: Human + Perplexity (半自動)
              → Perplexity用プロンプト自動生成→コピー
              → 調査結果をペースト→LLMがスコア化
              → Citation Share, センチメント (D6)
              → Global Citation (D7-03)

        ↓
  Score Aggregator (7領域均等配分 or 6領域加重平均)
        ↓
  改善提案エンジン ← 次のマイルストーン
    → 特定ページの具体的改善案を生成
    → SEO業者がクライアントに提案書として納品可能
```

### 7領域・28項目マッピング

| 領域 | カテゴリ | Engine | 項目数 |
|------|----------|--------|--------|
| D1 | 人：Trust Graph | E2+E3 | 4項目 |
| D2 | 技術：Extractability | E1 | 5項目 |
| D3 | 技術：Semantic Density | E1+E2 | 4項目 |
| D4 | 価値：Information Gain | E2 | 4項目 |
| D5 | 拡張：Multimodal & PR | E1+E3 | 4項目 |
| D6 | Audit：測定指標 | E3 | 3項目 |
| D7 | グローバル：Global Readiness | E1+E2 (optional) | 4項目 |

### スコア計算

- **6領域モード（Global OFF）**: D1-D6 加重平均（D1:20, D2:25, D3:15, D4:20, D5:10, D6:10）
- **7領域モード（Global ON）**: D1-D7 均等配分（各 100/7 ≒ 14.3%）
- **未評価項目は0点としてカウント**（領域の全項目数で割る）

### Tech Stack

- **Backend**: Python 3.11+
- **UI**: Streamlit + Plotly（レーダーチャート）
- **Deploy**: Streamlit Community Cloud
- **LLM**: BYOK方式（OpenAI API）
- **Scraping**: requests + BeautifulSoup4

## Development History

### 2026-04-04 — Gemini Session 1: 構想・指南書・インフォグラフィックス
- GEO指南書（完全保存版・1万字）を執筆完了
- 4コア・アプローチ（人・技術・価値・拡張）+ Audit = 6領域体系を確立
- インフォグラフィックス（縦長チェックリスト）をGemini画像生成で作成
- GitHub Private repo 作成、3-Engine構成設計、BYOK+ラチェット課金モデル設計

### 2026-04-04 — Claude Session 1: バックエンド完全実装
- README.md をLLMハンドオフ形式で作成
- `checklist/geo_checklist.json` — 6領域マスターデータ作成
- `core/static_crawler.py` — Engine 1 完全実装（11チェック）
- `core/llm_analyzer.py` — Engine 2 完全実装 + Auto-Fix機能
- `core/scoring.py` — スコア集計ロジック実装
- `app.py` — Streamlit MVP UI

### 2026-04-04 — Gemini Session 2: UI駆動開発・デプロイ・実動確認
- app2.pyでモックアップUI確認（Plotlyレーダー、st.status）
- ハイブリッド版app.pyを作成（Claude バックエンド + Gemini UI改善）
- Streamlit Community Cloudにデプロイ、picocela.com/en/で実動確認（52点/C）
- 外部データインポート機能追加（Perplexityプロンプトコピー、SNSペースト欄）
- D7 Global Readiness（英語露出評価）の構想確定

### 2026-04-05 — Claude Session 2: D7実装・スコア修正・Trust Graph統合
- `core/llm_analyzer.py` に Trust Graph解析（D1-01〜D1-03）追加
  - sns_data, px_data 引数追加（後方互換）
  - SNS/Perplexityデータがある場合のみAPI呼び出し
- D7 Global Readiness 全実装
  - `geo_checklist.json` にD7（4項目）追加 → 7領域28項目
  - `scoring.py` に global_mode 動的切替（6⇔7領域）
  - `static_crawler.py` に D7-02（Multi-Entity Linkage）自動判定追加
  - `llm_analyzer.py` に D7-01（EN-Social）, D7-04（EN-Content）追加
  - app.pyにサイドバートグル、7角形レーダー、グローバルタブ追加
- スコア計算修正
  - 未評価項目を0点としてカウント（全項目数で割る）
  - 7軸モードは均等配分に変更
- picocela.com/en/ で実動確認: 27点(D)（グローバルON、クイック解析）

## Known Issues

| Issue | Impact | Status |
|-------|--------|--------|
| Streamlit Private枠1つのみ | Low | 現在FusionGEOで使用中 |
| Engine 3 は半自動（Perplexityコピペ） | Medium | MVP段階ではこれで十分 |
| LLMプロンプト精度チューニング未実施 | Medium | 実データ蓄積後に調整 |
| 改善提案エンジンが未実装 | High | **コンサル販売のコア機能** |

## Next Actions

1. ⬜ **改善提案エンジン実装**（最優先）
   - 特定ページURLを入力 → 具体的改善案を生成
   - Before/After形式でリライト提案
   - JSON-LD/llms.txt のコード生成（コピペで使える）
   - SEO業者がクライアントに納品できるPDFレポート形式
2. ⬜ コミュニティ（PowerGPT 18,000人）投下用メッセージ作成
3. ⬜ Engine 2のプロンプト精度チューニング（実データ収集後）
4. ⬜ D7-03（Global Citation Share）の半自動化
5. ⬜ ホワイトラベル機能（SEO業者向け）
