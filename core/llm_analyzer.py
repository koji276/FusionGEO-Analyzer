"""
FusionGEO Analyzer — Engine 2: LLM Semantic Analyzer (AI Evaluation)
対象: D1-04, D2-04(補強), D3-04, D4-01, D4-02, D4-03
BYOK方式: ユーザーのAPIキーを使用
"""

import json
import re
from bs4 import BeautifulSoup

# ── OpenAI API呼び出し ──────────────────────────────────────────
def _call_openai(api_key: str, system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> str:
    """OpenAI APIを呼び出してテキスト応答を返す"""
    import openai
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=2000
    )
    return response.choices[0].message.content.strip()


def _extract_text_from_html(html: str, max_chars: int = 6000) -> str:
    """HTMLからメインコンテンツのテキストを抽出"""
    soup = BeautifulSoup(html, "html.parser")
    
    # script, style, nav, footer 除去
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    
    # article > section > body の優先順位
    content = soup.find("article") or soup.find("main") or soup.find("body")
    if content:
        text = content.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)
    
    # 空行除去
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    text = "\n".join(lines)
    
    return text[:max_chars]


# ═══════════════════════════════════════════════════════════════
# 統合LLM解析（1回のAPI呼び出しで複数項目を判定）
# ═══════════════════════════════════════════════════════════════

ANALYSIS_SYSTEM_PROMPT = """あなたはGEO（Generative Engine Optimization：生成エンジン最適化）の専門アナリストです。
Webページのテキストコンテンツを分析し、AIエージェント（ChatGPT, Perplexity等）に引用されやすいかを6つの観点から評価してください。

必ず以下のJSON形式のみで回答してください。説明文やマークダウンは不要です。

{
  "structure_score": {
    "score": 0-100の整数,
    "reason": "1行の日本語で理由"
  },
  "semantic_density": {
    "score": 0-100の整数,
    "entity_count": 検出した専門用語・概念の数,
    "reason": "1行の日本語で理由"
  },
  "first_party_data": {
    "score": 0-100の整数,
    "examples": ["検出した一次データの例（最大3つ）"],
    "reason": "1行の日本語で理由"
  },
  "pov_strength": {
    "score": 0-100の整数,
    "reason": "1行の日本語で理由"
  },
  "definitive_statements": {
    "score": 0-100の整数,
    "count": 検出した定義文の数,
    "examples": ["検出した定義文の例（最大3つ）"],
    "reason": "1行の日本語で理由"
  },
  "overall_geo_assessment": "AIに引用されやすさに関する2行の日本語の総合評価"
}

評価基準:
- structure_score (D1-04 / D2-04補強): 「結論→具体例→洞察」の構造か、段落が300文字以内か
- semantic_density (D3-04): 関連する専門用語・概念がどれだけ高密度に含まれているか
- first_party_data (D4-01): 独自調査、アンケート結果、導入事例など一次データの有無
- pov_strength (D4-02): 一般論でなく著者独自の鋭い視点・対立構造・予測があるか
- definitive_statements (D4-03): 「〇〇とは××である」のような断定的な定義文があるか
"""

ANALYSIS_USER_TEMPLATE = """以下のWebページのテキストコンテンツを分析してください。

===コンテンツ開始===
{content}
===コンテンツ終了===
"""

# ═══════════════════════════════════════════════════════════════
# Trust Graph解析（SNS + Perplexity外部データから D1-01〜D1-03 を判定）
# ═══════════════════════════════════════════════════════════════

TRUST_GRAPH_SYSTEM_PROMPT = """あなたはGEO（生成エンジン最適化）の専門アナリストです。
ユーザーが提供する「SNS/LinkedIn情報」と「外部メディア/AI引用調査」のデータを分析し、
発信者のTrust Graph（信頼性ネットワーク）を3つの観点からスコアリングしてください。

必ず以下のJSON形式のみで回答してください。説明文やマークダウンは不要です。

{
  "niche_authority": {
    "score": 0-100の整数,
    "detected_niche": "検出した専門領域（例：AI戦略 × 製造業）",
    "reason": "1行の日本語で理由"
  },
  "verified_identity": {
    "score": 0-100の整数,
    "platforms_found": ["検出したプラットフォーム名"],
    "reason": "1行の日本語で理由"
  },
  "engagement_graph": {
    "score": 0-100の整数,
    "metrics": "検出したエンゲージメント指標の要約",
    "reason": "1行の日本語で理由"
  }
}

評価基準:
- niche_authority (D1-01): 特定のニッチ領域の第一人者か。広すぎるテーマはスコアが下がる
- verified_identity (D1-02): LinkedIn/GitHub/メディア等で実名・経歴が検証可能か。sameAs紐付けがあるか
- engagement_graph (D1-03): 専門家コミュニティからのリアクション（いいね・コメント・引用）の量と質
"""

TRUST_GRAPH_USER_TEMPLATE = """以下の外部データから、発信者のTrust Graph（信頼性）を評価してください。

===SNS / LinkedIn情報===
{sns_data}
===SNS情報ここまで===

===外部メディア / AI引用調査（Perplexity等の結果）===
{px_data}
===外部調査ここまで===
"""


def _analyze_trust_graph(sns_data: str, px_data: str, api_key: str, model: str) -> list[dict]:
    """
    SNS/Perplexityデータから Trust Graph（D1-01〜D1-03）を判定。
    
    Returns:
        list of check_result dicts, or empty list if no data or error
    """
    # データが両方空なら何もしない（APIコストを使わない）
    if not sns_data.strip() and not px_data.strip():
        return []
    
    try:
        response = _call_openai(
            api_key=api_key,
            system_prompt=TRUST_GRAPH_SYSTEM_PROMPT,
            user_prompt=TRUST_GRAPH_USER_TEMPLATE.format(
                sns_data=sns_data or "（データなし）",
                px_data=px_data or "（データなし）"
            ),
            model=model
        )
        
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        
        data = json.loads(cleaned)
        
        checks = []
        checks.append({
            "id": "D1-01",
            "score": data["niche_authority"]["score"],
            "detected_niche": data["niche_authority"].get("detected_niche", ""),
            "detail": data["niche_authority"]["reason"]
        })
        checks.append({
            "id": "D1-02",
            "score": data["verified_identity"]["score"],
            "platforms_found": data["verified_identity"].get("platforms_found", []),
            "detail": data["verified_identity"]["reason"]
        })
        checks.append({
            "id": "D1-03",
            "score": data["engagement_graph"]["score"],
            "metrics": data["engagement_graph"].get("metrics", ""),
            "detail": data["engagement_graph"]["reason"]
        })
        
        return checks
        
    except Exception:
        # Trust Graph解析が失敗しても、メインの解析は止めない
        return []


def analyze_content_with_llm(html: str, api_key: str, model: str = "gpt-4o-mini",
                              sns_data: str = "", px_data: str = "") -> dict:
    """
    HTMLコンテンツをLLMで解析し、複数の観点のスコアを返す。
    sns_data/px_dataが提供された場合、Trust Graph（D1-01〜D1-03）も評価する。
    
    Args:
        html: ページのHTML
        api_key: ユーザーのOpenAI APIキー（BYOK）
        model: 使用するモデル
        sns_data: LinkedInの投稿やフォロワー数などのSNS情報（ユーザーがペースト）
        px_data: Perplexity等の外部調査結果（ユーザーがペースト）
    
    Returns:
        {
            "success": bool,
            "error": str | None,
            "checks": [check_result, ...],
            "overall_assessment": str
        }
    """
    result = {
        "success": False,
        "error": None,
        "checks": [],
        "overall_assessment": ""
    }
    
    text = _extract_text_from_html(html)
    if len(text) < 100:
        result["error"] = "テキストコンテンツが不足しています（100文字未満）"
        return result
    
    try:
        # ── Trust Graph解析（SNS/Perplexityデータがある場合のみ）──
        trust_checks = _analyze_trust_graph(sns_data, px_data, api_key, model)
        if trust_checks:
            result["checks"].extend(trust_checks)
        
        # ── コンテンツ品質解析（従来のメイン処理、変更なし）──
        response = _call_openai(
            api_key=api_key,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_prompt=ANALYSIS_USER_TEMPLATE.format(content=text),
            model=model
        )
        
        # JSON抽出（```json ... ``` 対応）
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        
        data = json.loads(cleaned)
        
        # チェック結果をマッピング（既存ロジックそのまま）
        result["checks"].append({
            "id": "D1-04",
            "score": data["structure_score"]["score"],
            "detail": data["structure_score"]["reason"]
        })
        result["checks"].append({
            "id": "D3-04",
            "score": data["semantic_density"]["score"],
            "entity_count": data["semantic_density"].get("entity_count", 0),
            "detail": data["semantic_density"]["reason"]
        })
        result["checks"].append({
            "id": "D4-01",
            "score": data["first_party_data"]["score"],
            "examples": data["first_party_data"].get("examples", []),
            "detail": data["first_party_data"]["reason"]
        })
        result["checks"].append({
            "id": "D4-02",
            "score": data["pov_strength"]["score"],
            "detail": data["pov_strength"]["reason"]
        })
        result["checks"].append({
            "id": "D4-03",
            "score": data["definitive_statements"]["score"],
            "count": data["definitive_statements"].get("count", 0),
            "examples": data["definitive_statements"].get("examples", []),
            "detail": data["definitive_statements"]["reason"]
        })
        
        result["overall_assessment"] = data.get("overall_geo_assessment", "")
        result["success"] = True
        
    except json.JSONDecodeError as e:
        result["error"] = f"LLM応答のJSON解析エラー: {str(e)}"
    except Exception as e:
        result["error"] = f"LLM解析エラー: {str(e)}"
    
    return result


# ═══════════════════════════════════════════════════════════════
# Auto-Fix: チャンク・リライト提案
# ═══════════════════════════════════════════════════════════════

REWRITE_SYSTEM_PROMPT = """あなたはGEO（生成エンジン最適化）の専門コンテンツエディターです。
与えられた段落を、AIエージェント（ChatGPT, Perplexity等）に引用されやすい形にリライトしてください。

ルール:
1. 300文字以内に収める
2. 冒頭1文に結論（Direct Answer）を配置
3. 具体的な数値やデータがあれば維持
4. 「〇〇とは××である」の定義文を含める
5. 段落のトピックは1つだけ

必ず以下のJSON形式のみで回答:
{
  "original_length": 元の文字数,
  "rewritten": "リライト後のテキスト",
  "rewritten_length": リライト後の文字数,
  "changes": ["変更点1", "変更点2"]
}
"""

def suggest_chunk_rewrite(paragraph: str, api_key: str, model: str = "gpt-4o-mini") -> dict:
    """長すぎる段落のリライト提案を生成"""
    try:
        response = _call_openai(
            api_key=api_key,
            system_prompt=REWRITE_SYSTEM_PROMPT,
            user_prompt=f"以下の段落をリライトしてください:\n\n{paragraph}",
            model=model
        )
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return {"success": True, **json.loads(cleaned)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# Auto-Fix: llms.txt 自動生成
# ═══════════════════════════════════════════════════════════════

LLMS_TXT_SYSTEM_PROMPT = """あなたはllms.txt仕様の専門家です。
与えられたWebページの情報から、AIエージェントが読み取りやすいllms.txtファイルの内容を生成してください。

llms.txt形式:
- 最初の行は「# サイト名」
- 続いて「> サイトの一行説明」
- その下に主要ページのリンクリスト（Markdown形式）

例:
# Example Corp
> AIを活用した製造業の業務改善コンサルティング
- [トップページ](https://example.com/)
- [サービス概要](https://example.com/services)
- [導入事例](https://example.com/cases)
- [ブログ](https://example.com/blog)

回答はllms.txtの内容のみ。説明やマークダウンのコードブロックは不要。
"""

def generate_llms_txt(url: str, html: str, api_key: str, model: str = "gpt-4o-mini") -> dict:
    """ページのHTMLからllms.txtを自動生成"""
    soup = BeautifulSoup(html, "html.parser")
    
    # ナビゲーションリンクを抽出
    nav_links = []
    nav = soup.find("nav") or soup.find("header")
    if nav:
        for a in nav.find_all("a", href=True)[:20]:
            text = a.get_text(strip=True)
            href = a["href"]
            if text and len(text) > 1 and not href.startswith("#"):
                nav_links.append(f"- [{text}]({href})")
    
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else url
    
    try:
        response = _call_openai(
            api_key=api_key,
            system_prompt=LLMS_TXT_SYSTEM_PROMPT,
            user_prompt=f"URL: {url}\nタイトル: {title_text}\n\nナビゲーションリンク:\n" + "\n".join(nav_links[:15]),
            model=model
        )
        return {"success": True, "content": response.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}
