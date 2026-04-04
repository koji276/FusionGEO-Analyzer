"""
FusionGEO Analyzer — Streamlit MVP
6領域・20項目のGEO完全監査ダッシュボード
BYOK（Bring Your Own Key）方式
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
from pathlib import Path

# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="FusionGEO Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Core Engine Import ─────────────────────────────────────
from core.static_crawler import analyze_url
from core.llm_analyzer import analyze_content_with_llm, generate_llms_txt, suggest_chunk_rewrite
from core.scoring import aggregate_scores, get_grade, DOMAIN_LABELS, DOMAIN_LABELS_SHORT

# ── チェックリスト読み込み ──────────────────────────────────
CHECKLIST_PATH = Path(__file__).parent / "checklist" / "geo_checklist.json"
with open(CHECKLIST_PATH, "r", encoding="utf-8") as f:
    CHECKLIST = json.load(f)

# ═══════════════════════════════════════════════════════════════
# サイドバー（BYOK設定）
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("FusionGEO")
    st.caption("by FUSIONDRIVER, INC.")
    st.divider()
    
    st.subheader("🔑 API Key (BYOK)")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="あなたのOpenAI APIキーを入力。FusionGEOは保存しません。"
    )
    
    llm_model = st.selectbox(
        "LLMモデル",
        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        help="Engine 2 のLLM解析に使用するモデル"
    )
    
    st.divider()
    st.subheader("📊 解析モード")
    analysis_mode = st.radio(
        "モード選択",
        ["🚀 フル解析（Engine 1+2）", "⚡ クイック解析（Engine 1のみ）"],
        help="フル解析はLLMを使用するためAPIクレジットを消費します"
    )
    
    st.divider()
    st.caption("v0.1 MVP — 6領域・20項目")
    st.caption("© 2026 FUSIONDRIVER, INC.")

# ═══════════════════════════════════════════════════════════════
# メインエリア
# ═══════════════════════════════════════════════════════════════
st.title("🔬 FusionGEO Analyzer")
st.markdown("**AIエージェントに引用される確率を、6領域・20項目で自動診断**")
st.markdown("---")

# ── URL入力 ──────────────────────────────────────────────
col_input, col_btn = st.columns([4, 1])
with col_input:
    target_url = st.text_input(
        "診断対象URL",
        placeholder="https://example.com/your-page",
        label_visibility="collapsed"
    )
with col_btn:
    analyze_btn = st.button("🔬 解析開始", type="primary", use_container_width=True)

# ── 解析実行 ──────────────────────────────────────────────
if analyze_btn and target_url:
    if not target_url.startswith("http"):
        st.error("URLは https:// から始まる形式で入力してください")
        st.stop()
    
    use_llm = "フル" in analysis_mode
    if use_llm and not api_key:
        st.warning("⚠️ フル解析にはAPIキーが必要です。サイドバーで設定してください。")
        st.stop()
    
    # ── Engine 1: 静的解析 ──────────────────────────────
    with st.spinner("🕷️ Engine 1: 静的クロール中..."):
        e1_result = analyze_url(target_url)
    
    if not e1_result["success"]:
        st.error(f"❌ ページ取得失敗: {e1_result['error']}")
        st.stop()
    
    st.success(f"✅ ページ取得成功: **{e1_result['page_title']}**")
    
    # ── Engine 2: LLM解析（オプション）──────────────────
    e2_result = None
    if use_llm:
        with st.spinner("🤖 Engine 2: LLMセマンティック解析中..."):
            page_html = requests.get(target_url, timeout=10).text
            e2_result = analyze_content_with_llm(page_html, api_key, llm_model)
        
        if e2_result and e2_result["success"]:
            st.success("✅ LLM解析完了")
        elif e2_result and e2_result["error"]:
            st.warning(f"⚠️ LLM解析エラー: {e2_result['error']}")
            e2_result = None
    
    # ── 手動チェック項目（Engine 3の代替）──────────────
    # MVP段階ではD1-01, D1-03, D5-02, D5-03, D6-01~03は自己申告
    manual_checks = {}
    
    # ── スコア集計 ──────────────────────────────────────
    scores = aggregate_scores(
        engine1_checks=e1_result["checks"],
        engine2_checks=e2_result["checks"] if e2_result and e2_result["success"] else None,
        manual_checks=manual_checks
    )
    
    grade, grade_label = get_grade(scores["total_score"])
    
    # ═══════════════════════════════════════════════════════
    # 結果表示
    # ═══════════════════════════════════════════════════════
    st.markdown("---")
    
    # ── ヘッダー: 総合スコア ──────────────────────────
    col_score, col_grade, col_assessment = st.columns([1, 1, 2])
    
    with col_score:
        st.metric(
            "総合GEOスコア",
            f"{scores['total_score']} / 100",
        )
    
    with col_grade:
        grade_colors = {"S": "🟢", "A": "🔵", "B": "🟡", "C": "🟠", "D": "🔴"}
        st.metric(
            "グレード",
            f"{grade_colors.get(grade, '')} {grade}",
        )
        st.caption(grade_label)
    
    with col_assessment:
        if e2_result and e2_result.get("overall_assessment"):
            st.info(f"🤖 **AI総合評価:** {e2_result['overall_assessment']}")
    
    st.markdown("---")
    
    # ── レーダーチャート ──────────────────────────────
    st.subheader("📡 6領域スコア")
    
    radar_df = pd.DataFrame(scores["radar_data"])
    
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        st.bar_chart(
            radar_df.set_index("domain")["score"],
            height=300,
        )
    
    with col_table:
        for item in scores["radar_data"]:
            score = item["score"]
            icon = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
            st.markdown(f"{icon} **{item['domain_full']}**: {score}/100")
    
    st.markdown("---")
    
    # ── 詳細結果（タブ） ──────────────────────────────
    st.subheader("🔍 詳細診断結果")
    
    tab_names = [f"{DOMAIN_LABELS_SHORT[f'D{i+1}']}" for i in range(6)]
    tabs = st.tabs(tab_names)
    
    for i, tab in enumerate(tabs):
        domain_id = f"D{i+1}"
        domain_info = CHECKLIST["domains"][i]
        
        with tab:
            st.markdown(f"### {domain_info['name']} ({domain_info['name_en']})")
            
            for item in domain_info["items"]:
                item_id = item["id"]
                check = scores["item_details"].get(item_id)
                
                if check:
                    score = check.get("score", 0)
                    detail = check.get("detail", "未評価")
                    
                    if score >= 75:
                        st.success(f"✅ **{item['title']}** — {score}/100\n\n{detail}")
                    elif score >= 40:
                        st.warning(f"⚠️ **{item['title']}** — {score}/100\n\n{detail}")
                    else:
                        st.error(f"❌ **{item['title']}** — {score}/100\n\n{detail}")
                else:
                    st.info(f"ℹ️ **{item['title']}** — 未評価（Engine 3 or 手動チェック対象）\n\n{item['description']}")
    
    st.markdown("---")
    
    # ── 改善優先アクション ──────────────────────────────
    st.subheader("🛠️ 優先改善アクション")
    
    priorities = scores["improvement_priorities"]
    if not priorities:
        st.success("🎉 すべての項目で良好なスコアです！")
    else:
        for idx, p in enumerate(priorities[:5], 1):
            with st.expander(f"**{idx}. [{p['id']}] スコア: {p['score']}/100** — {p['detail'][:60]}"):
                st.markdown(f"**改善アクション:** {p['action']}")
                
                # Auto-Fix ボタン
                if p["id"] == "D2-02" and use_llm:
                    if st.button(f"🪄 llms.txt を自動生成", key=f"fix_{p['id']}"):
                        with st.spinner("llms.txt を生成中..."):
                            page_html = requests.get(target_url, timeout=10).text
                            llms_result = generate_llms_txt(target_url, page_html, api_key, llm_model)
                        if llms_result["success"]:
                            st.code(llms_result["content"], language="markdown")
                            st.caption("↑ このテキストをドメイン直下に llms.txt として保存してください")
                        else:
                            st.error(f"生成エラー: {llms_result['error']}")
    
    st.markdown("---")
    st.caption("FusionGEO Analyzer v0.1 MVP — Powered by FUSIONDRIVER, INC.")
    st.caption("AIの知識グラフの中枢に陣取る。")

elif not target_url and analyze_btn:
    st.warning("URLを入力してください")

else:
    # ── ランディング画面 ──────────────────────────────
    st.markdown("""
    ### 使い方
    
    1. **サイドバー** でOpenAI APIキーを入力（BYOK方式 — キーは保存されません）
    2. **診断対象URL** を入力
    3. **🔬 解析開始** をクリック
    
    ### 診断する6つの領域
    
    | 領域 | 概要 |
    |------|------|
    | 🧑 **人 (Trust Graph)** | 発信者の専門性・信頼ネットワーク |
    | 🔧 **技術 (Extractability)** | robots.txt, llms.txt, セマンティックHTML |
    | 🔗 **技術 (Semantic Density)** | 構造化データ, Schema.org, FAQ/HowTo |
    | 💎 **価値 (Information Gain)** | 一次データ, 独自視点, 定義文, 鮮度 |
    | 🌐 **拡張 (Multimodal & PR)** | 画像最適化, 動画構造化, 共起性 |
    | 📊 **Audit (測定指標)** | Citation Share, センチメント, ログ分析 |
    """)
