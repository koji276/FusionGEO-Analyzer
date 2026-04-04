# FusionGEO Analyzer

URLを入力するだけで「AIエージェントに引用される確率」を6領域・20項目で自動診断し、改善提案まで出すSaaSツール。BYOK（APIキー持ち込み）+ ラチェット型従量課金モデル。

## Current Status

| Item | Status | Notes |
|------|--------|-------|
| GitHub Repo | ✅ Created (Private) | `koji276/FusionGEO-Analyzer` |
| GEO Checklist (6領域20項目) | ✅ Confirmed | See `checklist/geo_checklist.json` |
| Infographic (チェックリスト画像) | ✅ Generated | Gemini生成、PNG完成済み |
| Blog/指南書 (完全保存版) | ✅ Written | Geminiセッションで1万字版完成 |
| Architecture Design | ✅ Designed | 3-Engine構成（下記参照） |
| Pricing Model | ✅ Designed | BYOK + ラチェット従量課金 |
| Core Engine 1 (Static Crawler) | 🔧 In Progress | `core/static_crawler.py` — 骨格のみ |
| Core Engine 2 (LLM Semantic) | ⬜ Not Started | `core/llm_analyzer.py` |
| Core Engine 3 (Trust/Citation) | ⬜ Not Started | `core/trust_engine.py` |
| Streamlit UI (app.py) | 🔧 In Progress | 骨格のみ、要リビルド |
| Auto-Fix: llms.txt Generator | ⬜ Not Started | キラー機能 |
| Auto-Fix: Chunk Rewriter | ⬜ Not Started | キラー機能 |

## Architecture

### 3-Engine構成

```
User Input (URL + BYOK API Key)
        │
        ├─► Engine 1: Static Crawler (Rule-Based)
        │     Python (requests + BeautifulSoup)
        │     → robots.txt解析、llms.txt存在チェック
        │     → セマンティックHTML判定、Schema.org検出
        │     → <time>タグ鮮度チェック、JS依存判定
        │
        ├─► Engine 2: LLM Semantic Analyzer (AI Evaluation)
        │     BYOK API (GPT-4o / Claude etc.)
        │     → チャンク化品質判定（段落長・結論位置）
        │     → Information Gain判定（一次データ有無）
        │     → POV強度評価（独自視点の鋭さ）
        │     → 専門用語定義の検出
        │
        └─► Engine 3: Trust & Citation Engine
              外部API (Perplexity/Tavily等)
              → Citation Share計測
              → Entity共起チェック
              → Verified Identity確認
              
        ↓
  Score Aggregator (6領域レーダーチャート)
        ↓
  Auto-Fix Generator
    → llms.txt自動生成
    → チャンク・リライト提案
    → JSON-LD構造化データ生成
```

### 6領域・20項目マッピング

| 領域 | カテゴリ | Engine | 項目数 |
|------|----------|--------|--------|
| 領域1 | 人：Trust Graph | E2+E3 | 4項目 |
| 領域2 | 技術：Extractability | E1 | 5項目 |
| 領域3 | 技術：Semantic Density | E1+E2 | 4項目 |
| 領域4 | 価値：Information Gain | E2 | 4項目 |
| 領域5 | 拡張：Multimodal & PR | E2+E3 | 4項目 |
| 領域6 | Audit：測定指標 | E3 | 3項目 |

### Tech Stack

- **Backend**: Python 3.11+
- **UI**: Streamlit (MVP) → React + Next.js (Production SaaS)
- **Deploy**: Streamlit Community Cloud (MVP, Private枠1つ使用)
- **LLM**: BYOK方式（ユーザーがOpenAI/Anthropic APIキーを入力）
- **Scraping**: requests + BeautifulSoup4
- **Data**: pandas, numpy

### Pricing Model (BYOK + Ratchet)

```
Base Fee:        $99/mo (ダッシュボード利用)
Credits:         1 URL診断 = 1 credit
                 改善提案生成 = 3 credits
Ratchet Tiers:   一度到達したTierの最低保証額は下がらない
LLM API Cost:    ユーザー負担（BYOK）
```

## Development History

### 2025-04-04 — Project Inception (Gemini Session)
- GEO指南書（完全保存版・1万字）をGeminiで執筆完了
- 4コア・アプローチ（人・技術・価値・拡張）+ Audit = 6領域・20項目体系を確立
- インフォグラフィックス（縦長チェックリスト）をGemini画像生成で作成
- GitHub Private repo `koji276/FusionGEO-Analyzer` 作成
- requirements.txt, app.py, core/static_crawler.py の骨格をGitHubに直接書き込み
- 3-Engine構成のアーキテクチャ設計完了
- BYOK + ラチェット型従量課金のビジネスモデル設計完了
- SEO業者向けホワイトラベル提供・API連携・認定パートナー制度を構想

### 2025-04-04 — Claude Session: Engine Implementation Start
- README.md をLLMハンドオフ形式で作成
- `checklist/geo_checklist.json` — 6領域20項目のマスターデータ作成
- `core/static_crawler.py` — Engine 1 完全実装
- `core/llm_analyzer.py` — Engine 2 完全実装
- `core/scoring.py` — スコア集計ロジック実装
- `app.py` — Streamlit MVP UI リビルド

## Known Issues

| Issue | Impact | Status |
|-------|--------|--------|
| Streamlit Private枠が1つしかない（無料プラン） | Medium | FusionAutoScan等と枠競合の可能性 |
| Engine 3 (Trust/Citation) は外部API依存 | Low | MVP段階では自己申告チェックボックスで代替可 |
| LLMプロンプトの精度チューニング未実施 | Medium | コミュニティ投下後にデータ収集して調整 |

## Next Actions

1. ✅ README.md 作成（LLMハンドオフ形式）
2. ✅ `checklist/geo_checklist.json` 作成（20項目マスター）
3. ✅ `core/static_crawler.py` Engine 1 完全実装
4. ✅ `core/llm_analyzer.py` Engine 2 実装
5. ✅ `core/scoring.py` スコア集計ロジック
6. ✅ `app.py` Streamlit MVP リビルド
7. ⬜ GitHub repo にpush（既存ファイル上書き）
8. ⬜ Streamlit Community Cloud デプロイ
9. ⬜ コミュニティ（PowerGPT 18,000人）投下用メッセージ作成
10. ⬜ Engine 3 (Trust/Citation) 実装
11. ⬜ Auto-Fix機能（llms.txt生成、チャンク・リライト）実装
