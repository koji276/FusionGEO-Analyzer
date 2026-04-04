import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os

# ==========================================
# 安全のためのモック関数（coreファイルがない場合の保険）
# ==========================================
def mock_static_crawl(url):
    time.sleep(2)
    return {
        "status": "success",
        "url": url,
        "robots_txt_exists": True,
        "llms_txt_exists": False,
        "has_schema_org": True,
        "extractability_score": 75,
        "raw_html_length": 15000
    }

# ==========================================
# Engine 1 の読み込み試行
# ==========================================
# core/static_crawler.py が存在すれば読み込む
try:
    from core.static_crawler import run_static_analysis
    ENGINE_1_AVAILABLE = True
except ImportError:
    run_static_analysis = mock_static_crawl
    ENGINE_1_AVAILABLE = False

# ==========================================
# UI 構築
# ==========================================
st.set_page_config(page_title="FusionGEO Analyzer (Dev)", layout="wide")

st.title("🔍 FusionGEO Analyzer - Dev Mode")

# エンジン接続状況の表示
if ENGINE_1_AVAILABLE:
    st.success("✅ Engine 1 (Static Crawler) is connected!")
else:
    st.warning("⚠️ Engine 1 (core/static_crawler.py) is missing or has an error. Using Mock Engine.")

with st.sidebar:
    st.header("⚙️ 設定 (BYOK)")
    api_key = st.text_input("API Key", type="password")
    st.divider()
    st.write("Status: Development Mode")

url = st.text_input("診断対象のURLを入力", placeholder="https://...", value="https://picocela.com/en/")

if st.button("診断開始", type="primary"):
    if url:
        # ==========================================
        # Engine 1 実行
        # ==========================================
        with st.status("サイト構造を解析中...", expanded=True) as status:
            st.write("Engine 1: クローラー起動...")
            
            # ここで実際の処理（またはモック）が走る
            result = run_static_analysis(url)
            
            st.write(f"robots.txt 確認: {'✅' if result.get('robots_txt_exists') else '❌'}")
            st.write(f"llms.txt 確認: {'✅' if result.get('llms_txt_exists') else '❌'}")
            st.write(f"構造化データ 確認: {'✅' if result.get('has_schema_org') else '❌'}")
            
            status.update(label="Engine 1 分析完了！", state="complete", expanded=False)
        
        # ==========================================
        # 結果表示
        # ==========================================
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📊 スコア推移 (抽出性のみリアル)")
            
            # Engine1から得た「抽出性」スコアを反映（他はダミー）
            extract_score = result.get('extractability_score', 50)
            
            df = pd.DataFrame(dict(
                theta=['信頼性', '抽出性', '意味密度', '独自性', '拡張性', '監査'],
                r=[80, extract_score, 90, 70, 50, 85]  # 抽出性のみ動的
            ))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,100])
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.subheader("📝 改善のアクション (Engine 1)")
            
            if result.get('has_schema_org'):
                st.success("✅ 構造化データ(JSON-LD)が検出されました。")
            else:
                st.warning("⚠️ 構造化データ(JSON-LD)が見つかりません。追加を推奨します。")
                
            if not result.get('llms_txt_exists'):
                st.warning("⚠️ llms.txt が見つかりません。")
                if st.button("✨ llms.txt を自動生成"):
                    st.code(f"User-agent: *\nAllow: /\n\n# Source: {url}", language="text")
            else:
                st.success("✅ llms.txt が適切に設定されています。")
                
    else:
        st.error("URLを入力してください。")
