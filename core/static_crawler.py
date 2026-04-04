"""
FusionGEO Analyzer — Engine 1: Static Crawler (Rule-Based)
対象: D2 (Extractability), D3 (Semantic Density), D4-04 (Freshness), D5 (Multimodal)
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import json
import re

TIMEOUT = 10
HEADERS = {
    "User-Agent": "FusionGEO-Analyzer/1.0 (https://fusiondriver.biz)"
}

# ── AI Bot signatures ──────────────────────────────────────────
TRAINING_BOTS = ["GPTBot", "Google-Extended", "CCBot", "anthropic-ai"]
SEARCH_BOTS = ["OAI-SearchBot", "PerplexityBot", "ChatGPT-User", "ClaudeBot"]


def _get(url: str, timeout: int = TIMEOUT) -> requests.Response | None:
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def _get_domain(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


# ═══════════════════════════════════════════════════════════════
# D2-01: robots.txt 交通整理
# ═══════════════════════════════════════════════════════════════
def check_robots_txt(url: str) -> dict:
    """robots.txt を解析し、学習用Bot制限 + 引用用Bot許可の状態を判定"""
    domain = _get_domain(url)
    resp = _get(f"{domain}/robots.txt")
    
    result = {
        "id": "D2-01",
        "score": 0,        # 0 / 50 / 100
        "exists": False,
        "training_bots_blocked": [],
        "search_bots_allowed": [],
        "detail": ""
    }
    
    if not resp or resp.status_code != 200:
        result["detail"] = "robots.txt が見つかりません"
        return result
    
    result["exists"] = True
    content = resp.text.lower()
    raw = resp.text
    
    # 学習用Botが制限されているか
    for bot in TRAINING_BOTS:
        # User-agent: GPTBot → Disallow: / のパターン検出
        pattern = re.compile(
            rf"user-agent:\s*{bot.lower()}.*?disallow:\s*/",
            re.DOTALL
        )
        if pattern.search(content):
            result["training_bots_blocked"].append(bot)
    
    # 引用用Botが許可されているか
    for bot in SEARCH_BOTS:
        bot_lower = bot.lower()
        # 明示的に許可 or ブロックされていない
        if bot_lower in content:
            # Disallow: / がないか確認
            block_pattern = re.compile(
                rf"user-agent:\s*{bot_lower}.*?disallow:\s*/",
                re.DOTALL
            )
            if not block_pattern.search(content):
                result["search_bots_allowed"].append(bot)
        else:
            # 言及なし = デフォルト許可
            result["search_bots_allowed"].append(bot)
    
    # スコアリング
    has_training_block = len(result["training_bots_blocked"]) > 0
    has_search_allow = len(result["search_bots_allowed"]) > 0
    
    if has_training_block and has_search_allow:
        result["score"] = 100
        result["detail"] = "学習Botを制限しつつ、引用Botを許可する理想的な設定"
    elif has_search_allow:
        result["score"] = 50
        result["detail"] = "引用Botは許可されているが、学習Botの制限が未設定"
    else:
        result["score"] = 0
        result["detail"] = "Botの交通整理が未実施"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D2-02: llms.txt / llms-full.txt
# ═══════════════════════════════════════════════════════════════
def check_llms_txt(url: str) -> dict:
    """llms.txt と llms-full.txt の存在・内容を確認"""
    domain = _get_domain(url)
    result = {
        "id": "D2-02",
        "score": 0,
        "llms_txt": False,
        "llms_full_txt": False,
        "llms_txt_lines": 0,
        "detail": ""
    }
    
    resp = _get(f"{domain}/llms.txt")
    if resp and resp.status_code == 200 and len(resp.text.strip()) > 10:
        result["llms_txt"] = True
        result["llms_txt_lines"] = len(resp.text.strip().split("\n"))
    
    resp_full = _get(f"{domain}/llms-full.txt")
    if resp_full and resp_full.status_code == 200 and len(resp_full.text.strip()) > 50:
        result["llms_full_txt"] = True
    
    if result["llms_txt"] and result["llms_full_txt"]:
        result["score"] = 100
        result["detail"] = f"llms.txt ({result['llms_txt_lines']}行) + llms-full.txt 完備"
    elif result["llms_txt"]:
        result["score"] = 70
        result["detail"] = f"llms.txt あり ({result['llms_txt_lines']}行)、llms-full.txt 未設置"
    else:
        result["score"] = 0
        result["detail"] = "llms.txt 未設置 — AI専用サイトマップがありません"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D2-03: セマンティックHTML
# ═══════════════════════════════════════════════════════════════
def check_semantic_html(soup: BeautifulSoup) -> dict:
    """article, section, aside, main, nav等のセマンティックタグの使用状況"""
    result = {
        "id": "D2-03",
        "score": 0,
        "tags_found": {},
        "detail": ""
    }
    
    semantic_tags = ["article", "section", "main", "aside", "nav", "header", "footer"]
    for tag in semantic_tags:
        count = len(soup.find_all(tag))
        if count > 0:
            result["tags_found"][tag] = count
    
    has_article = "article" in result["tags_found"]
    has_section = "section" in result["tags_found"]
    has_main = "main" in result["tags_found"]
    
    if has_article and (has_section or has_main):
        result["score"] = 100
        result["detail"] = f"セマンティックHTML適切: {result['tags_found']}"
    elif has_article or has_section:
        result["score"] = 70
        result["detail"] = f"セマンティックタグ一部使用: {result['tags_found']}"
    elif len(result["tags_found"]) > 0:
        result["score"] = 30
        result["detail"] = f"基本タグのみ: {result['tags_found']}"
    else:
        result["score"] = 0
        result["detail"] = "セマンティックHTMLタグが未使用 — divのみの構造"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D2-04: チャンク化設計（段落長の統計分析）
# ═══════════════════════════════════════════════════════════════
def check_chunking(soup: BeautifulSoup) -> dict:
    """段落（<p>タグ）の文字数分布を解析し、チャンク化の品質を判定"""
    result = {
        "id": "D2-04",
        "score": 0,
        "total_paragraphs": 0,
        "avg_length": 0,
        "over_300_count": 0,
        "under_60_with_conclusion_count": 0,
        "detail": ""
    }
    
    paragraphs = soup.find_all("p")
    lengths = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 10:  # 空段落除外
            lengths.append(len(text))
    
    if not lengths:
        result["detail"] = "コンテンツ段落が検出されません"
        return result
    
    result["total_paragraphs"] = len(lengths)
    result["avg_length"] = round(sum(lengths) / len(lengths))
    result["over_300_count"] = sum(1 for l in lengths if l > 300)
    
    over_ratio = result["over_300_count"] / len(lengths)
    
    if over_ratio <= 0.1 and result["avg_length"] <= 200:
        result["score"] = 100
        result["detail"] = f"優秀: 平均{result['avg_length']}文字/段落、300文字超は{result['over_300_count']}段落のみ"
    elif over_ratio <= 0.3:
        result["score"] = 60
        result["detail"] = f"改善余地あり: 平均{result['avg_length']}文字、{result['over_300_count']}段落が300文字超"
    else:
        result["score"] = 20
        result["detail"] = f"要改善: {result['over_300_count']}/{len(lengths)}段落が300文字超（AIが抽出しにくい）"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D2-05: JS実行依存の解消
# ═══════════════════════════════════════════════════════════════
def check_js_dependency(soup: BeautifulSoup, raw_html: str) -> dict:
    """初期HTMLにコンテンツがあるか、JS依存度を判定"""
    result = {
        "id": "D2-05",
        "score": 0,
        "text_in_html": 0,
        "script_tags": 0,
        "has_noscript": False,
        "spa_framework_detected": None,
        "detail": ""
    }
    
    # テキスト量
    body = soup.find("body")
    if body:
        text_content = body.get_text(strip=True)
        result["text_in_html"] = len(text_content)
    
    result["script_tags"] = len(soup.find_all("script"))
    result["has_noscript"] = soup.find("noscript") is not None
    
    # SPA検出
    spa_markers = {
        "react": ["__next", "react-root", "_next/static"],
        "vue": ["__vue", "v-app"],
        "angular": ["ng-app", "ng-version"],
    }
    for fw, markers in spa_markers.items():
        for marker in markers:
            if marker in raw_html:
                result["spa_framework_detected"] = fw
                break
    
    # 判定
    if result["text_in_html"] > 500 and not result["spa_framework_detected"]:
        result["score"] = 100
        result["detail"] = f"初期HTMLに{result['text_in_html']}文字のコンテンツ — JS非依存"
    elif result["text_in_html"] > 200:
        result["score"] = 60
        result["detail"] = f"初期HTMLに{result['text_in_html']}文字あるが、{result['spa_framework_detected'] or 'JS'}への依存もあり"
    else:
        result["score"] = 10
        fw = result["spa_framework_detected"] or "JavaScript"
        result["detail"] = f"初期HTMLにコンテンツがほぼなし — {fw}レンダリング依存（AIクローラーに不利）"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D3-01: Schema.org (Entity証明)
# ═══════════════════════════════════════════════════════════════
def check_schema_org(soup: BeautifulSoup) -> dict:
    """JSON-LD構造化データの存在とEntity関連プロパティの検出"""
    result = {
        "id": "D3-01",
        "score": 0,
        "json_ld_found": False,
        "types_detected": [],
        "has_sameAs": False,
        "has_author": False,
        "detail": ""
    }
    
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    if not scripts:
        result["detail"] = "JSON-LD構造化データが未設置"
        return result
    
    result["json_ld_found"] = True
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if "@type" in item:
                    t = item["@type"]
                    if isinstance(t, list):
                        result["types_detected"].extend(t)
                    else:
                        result["types_detected"].append(t)
                if "sameAs" in item:
                    result["has_sameAs"] = True
                if "author" in item:
                    result["has_author"] = True
                # @graph 対応
                if "@graph" in item:
                    for g in item["@graph"]:
                        if "@type" in g:
                            result["types_detected"].append(g["@type"])
                        if "sameAs" in g:
                            result["has_sameAs"] = True
                        if "author" in g:
                            result["has_author"] = True
        except (json.JSONDecodeError, TypeError):
            continue
    
    result["types_detected"] = list(set(result["types_detected"]))
    
    entity_types = {"Person", "Organization", "Corporation", "LocalBusiness"}
    has_entity = bool(entity_types & set(result["types_detected"]))
    
    if has_entity and result["has_sameAs"]:
        result["score"] = 100
        result["detail"] = f"Entity証明あり: {result['types_detected']}、sameAs紐付けあり"
    elif has_entity or result["has_author"]:
        result["score"] = 60
        result["detail"] = f"部分的: {result['types_detected']}、sameAs未設定"
    elif result["json_ld_found"]:
        result["score"] = 30
        result["detail"] = f"JSON-LDあるがEntity型なし: {result['types_detected']}"
    else:
        result["score"] = 0
        result["detail"] = "構造化データなし"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D3-02: SignificantLink
# ═══════════════════════════════════════════════════════════════
def check_significant_link(soup: BeautifulSoup) -> dict:
    """significantLink プロパティの検出"""
    result = {
        "id": "D3-02",
        "score": 0,
        "found": False,
        "detail": ""
    }
    
    # JSON-LDで検索
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            text = script.string or ""
            if "significantLink" in text or "significantlink" in text.lower():
                result["found"] = True
                break
        except Exception:
            continue
    
    # itemprop属性で検索
    if not result["found"]:
        sig_links = soup.find_all(attrs={"itemprop": "significantLink"})
        if sig_links:
            result["found"] = True
    
    result["score"] = 100 if result["found"] else 0
    result["detail"] = "SignificantLink 実装済み" if result["found"] else "SignificantLink 未実装"
    return result


# ═══════════════════════════════════════════════════════════════
# D3-03: FAQ & HowTo スキーマ
# ═══════════════════════════════════════════════════════════════
def check_faq_howto(soup: BeautifulSoup) -> dict:
    """FAQPage, HowTo スキーマの検出"""
    result = {
        "id": "D3-03",
        "score": 0,
        "faq_found": False,
        "howto_found": False,
        "detail": ""
    }
    
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            text = script.string or ""
            if "FAQPage" in text:
                result["faq_found"] = True
            if "HowTo" in text:
                result["howto_found"] = True
        except Exception:
            continue
    
    if result["faq_found"] and result["howto_found"]:
        result["score"] = 100
        result["detail"] = "FAQ + HowTo 両方のスキーマ設置済み"
    elif result["faq_found"] or result["howto_found"]:
        result["score"] = 70
        which = "FAQ" if result["faq_found"] else "HowTo"
        result["detail"] = f"{which}スキーマあり、もう一方は未設置"
    else:
        result["score"] = 0
        result["detail"] = "FAQ/HowToスキーマ未設置 — AI回答への採用率が低下"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D4-04: フレッシュネス（鮮度）
# ═══════════════════════════════════════════════════════════════
def check_freshness(soup: BeautifulSoup) -> dict:
    """<time>タグや meta で最終更新日を取得し、60日ルールで判定"""
    result = {
        "id": "D4-04",
        "score": 0,
        "last_updated": None,
        "days_ago": None,
        "detail": ""
    }
    
    # <time datetime="..."> を探す
    time_tags = soup.find_all("time")
    dates = []
    for t in time_tags:
        dt = t.get("datetime", "")
        if dt:
            dates.append(dt)
    
    # meta タグ
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "")
        if "modified" in prop.lower() or "updated" in prop.lower():
            content = meta.get("content", "")
            if content:
                dates.append(content)
    
    # 日付パース
    now = datetime.now(timezone.utc)
    best_date = None
    for d in dates:
        try:
            parsed = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if best_date is None or parsed > best_date:
                best_date = parsed
        except ValueError:
            # 他の形式を試す
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y"]:
                try:
                    parsed = datetime.strptime(d, fmt).replace(tzinfo=timezone.utc)
                    if best_date is None or parsed > best_date:
                        best_date = parsed
                    break
                except ValueError:
                    continue
    
    if best_date:
        days = (now - best_date).days
        result["last_updated"] = best_date.isoformat()
        result["days_ago"] = days
        
        if days <= 60:
            result["score"] = 100
            result["detail"] = f"鮮度良好: {days}日前に更新（60日ルール内）"
        elif days <= 180:
            result["score"] = 50
            result["detail"] = f"要更新: {days}日前の更新（60日ルール超過）"
        else:
            result["score"] = 10
            result["detail"] = f"古い情報: {days}日前の更新 — RAGで弾かれるリスク大"
    else:
        result["score"] = 0
        result["detail"] = "更新日時の明示なし（<time>タグやmeta未設置）"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D5-01: VLM最適化（画像alt属性）
# ═══════════════════════════════════════════════════════════════
def check_image_alt(soup: BeautifulSoup) -> dict:
    """画像のalt属性とコンテキスト（周辺テキスト・figcaption）の充実度"""
    result = {
        "id": "D5-01",
        "score": 0,
        "total_images": 0,
        "with_alt": 0,
        "with_figcaption": 0,
        "detail": ""
    }
    
    images = soup.find_all("img")
    result["total_images"] = len(images)
    
    if not images:
        result["score"] = 100  # 画像がなければN/A扱い
        result["detail"] = "画像なし（判定対象外）"
        return result
    
    for img in images:
        alt = img.get("alt", "").strip()
        if alt and len(alt) > 5:
            result["with_alt"] += 1
        # figcaption チェック
        parent = img.parent
        if parent and parent.name == "figure":
            fc = parent.find("figcaption")
            if fc and len(fc.get_text(strip=True)) > 5:
                result["with_figcaption"] += 1
    
    alt_ratio = result["with_alt"] / result["total_images"]
    
    if alt_ratio >= 0.9:
        result["score"] = 100
        result["detail"] = f"{result['with_alt']}/{result['total_images']}画像にalt属性あり"
    elif alt_ratio >= 0.5:
        result["score"] = 50
        result["detail"] = f"alt不足: {result['with_alt']}/{result['total_images']}画像のみ"
    else:
        result["score"] = 10
        result["detail"] = f"VLM最適化不十分: {result['total_images']}画像中{result['with_alt']}のみalt設定"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D5-04: 外部引用リンク（情報の透明性）
# ═══════════════════════════════════════════════════════════════
def check_outbound_citations(soup: BeautifulSoup, url: str) -> dict:
    """外部ドメインへの引用リンク数とその権威性を判定"""
    result = {
        "id": "D5-04",
        "score": 0,
        "outbound_links": 0,
        "authority_domains": [],
        "detail": ""
    }
    
    own_domain = urlparse(url).netloc
    authority_markers = [
        "wikipedia.org", "arxiv.org", "github.com", "scholar.google",
        ".gov", ".edu", ".ac.jp", "pubmed", "nature.com", "ieee.org",
        "semrush.com", "similarweb.com", "statista.com"
    ]
    
    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"]
        if href.startswith("http") and own_domain not in href:
            result["outbound_links"] += 1
            for marker in authority_markers:
                if marker in href:
                    result["authority_domains"].append(href)
                    break
    
    result["authority_domains"] = result["authority_domains"][:10]  # 上限
    
    if result["outbound_links"] >= 3 and len(result["authority_domains"]) >= 1:
        result["score"] = 100
        result["detail"] = f"外部引用{result['outbound_links']}件（権威ドメイン{len(result['authority_domains'])}件含む）"
    elif result["outbound_links"] >= 2:
        result["score"] = 50
        result["detail"] = f"外部リンク{result['outbound_links']}件あるが、権威ドメインへの参照不足"
    else:
        result["score"] = 10
        result["detail"] = f"外部引用{result['outbound_links']}件のみ — 情報ハブとしての信頼性が低い"
    
    return result


# ═══════════════════════════════════════════════════════════════
# D7-02: Multi-Entity Linkage（日英エンティティ紐付け）
# ═══════════════════════════════════════════════════════════════
def check_global_entity_linkage(soup: BeautifulSoup, url: str) -> dict:
    """hreflang、英語版リンク、多言語sameAsの検出"""
    result = {
        "id": "D7-02",
        "score": 0,
        "has_hreflang": False,
        "has_en_alternate": False,
        "en_sameAs_found": False,
        "detail": ""
    }
    
    signals = 0
    
    # hreflangタグの検出
    hreflangs = soup.find_all("link", {"rel": "alternate", "hreflang": True})
    if hreflangs:
        result["has_hreflang"] = True
        signals += 1
        # 英語版が含まれるか
        for tag in hreflangs:
            lang = tag.get("hreflang", "").lower()
            if lang.startswith("en"):
                result["has_en_alternate"] = True
                signals += 1
                break
    
    # HTMLのlang属性チェック
    html_tag = soup.find("html")
    page_lang = html_tag.get("lang", "").lower() if html_tag else ""
    is_english_page = page_lang.startswith("en")
    if is_english_page:
        signals += 1
    
    # 英語版ナビゲーションリンク（/en/, /english/, ?lang=en 等）
    en_link_patterns = ["/en/", "/en-", "/english", "lang=en", "/intl/"]
    for a in soup.find_all("a", href=True)[:100]:
        href = a.get("href", "").lower()
        for pattern in en_link_patterns:
            if pattern in href:
                signals += 1
                break
        if signals >= 4:
            break
    
    # JSON-LDのsameAsで外国語サイトへの紐付け
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            text = script.string or ""
            if "sameAs" in text:
                # LinkedIn, GitHub等の英語プラットフォームへの紐付け
                if any(p in text for p in ["linkedin.com", "github.com", "twitter.com", "x.com"]):
                    result["en_sameAs_found"] = True
                    signals += 1
        except Exception:
            continue
    
    # スコアリング
    if signals >= 4:
        result["score"] = 100
        result["detail"] = "多言語対応優秀: hreflang、英語版ページ、グローバルEntity紐付けあり"
    elif signals >= 2:
        result["score"] = 60
        result["detail"] = f"部分的な多言語対応: {signals}個のシグナル検出"
    elif signals >= 1:
        result["score"] = 30
        result["detail"] = f"最低限のグローバル対応: {signals}個のシグナルのみ"
    else:
        result["score"] = 0
        result["detail"] = "多言語対応なし — 英語圏AIからのEntity認識が困難"
    
    return result


# ═══════════════════════════════════════════════════════════════
# メイン: 全チェック実行
# ═══════════════════════════════════════════════════════════════
def analyze_url(url: str) -> dict:
    """
    指定URLに対してEngine 1の全チェックを実行し、結果を返す。
    
    Returns:
        {
            "url": str,
            "success": bool,
            "error": str | None,
            "checks": [check_result, ...],
            "page_title": str
        }
    """
    result = {
        "url": url,
        "success": False,
        "error": None,
        "checks": [],
        "page_title": ""
    }
    
    # ページ取得
    resp = _get(url)
    if not resp or resp.status_code != 200:
        result["error"] = f"ページ取得失敗 (status: {resp.status_code if resp else 'timeout'})"
        return result
    
    raw_html = resp.text
    soup = BeautifulSoup(raw_html, "html.parser")
    
    title_tag = soup.find("title")
    result["page_title"] = title_tag.get_text(strip=True) if title_tag else "(タイトルなし)"
    
    # 全チェック実行
    result["checks"].append(check_robots_txt(url))          # D2-01
    result["checks"].append(check_llms_txt(url))             # D2-02
    result["checks"].append(check_semantic_html(soup))       # D2-03
    result["checks"].append(check_chunking(soup))            # D2-04
    result["checks"].append(check_js_dependency(soup, raw_html))  # D2-05
    result["checks"].append(check_schema_org(soup))          # D3-01
    result["checks"].append(check_significant_link(soup))    # D3-02
    result["checks"].append(check_faq_howto(soup))           # D3-03
    result["checks"].append(check_freshness(soup))           # D4-04
    result["checks"].append(check_image_alt(soup))           # D5-01
    result["checks"].append(check_outbound_citations(soup, url))  # D5-04
    result["checks"].append(check_global_entity_linkage(soup, url))  # D7-02
    
    result["success"] = True
    return result


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    results = analyze_url(test_url)
    print(json.dumps(results, indent=2, ensure_ascii=False))
