"""
FusionGEO Analyzer — Score Aggregator
Engine 1 + Engine 2 の結果を6（or 7）領域に集約し、レーダーチャートデータを生成
"""

import json
from pathlib import Path

# チェックリスト定義読み込み
CHECKLIST_PATH = Path(__file__).parent.parent / "checklist" / "geo_checklist.json"

# 各チェック項目がどの領域に属するか
ITEM_TO_DOMAIN = {
    # D1: Trust Graph
    "D1-01": "D1", "D1-02": "D1", "D1-03": "D1", "D1-04": "D1",
    # D2: Extractability
    "D2-01": "D2", "D2-02": "D2", "D2-03": "D2", "D2-04": "D2", "D2-05": "D2",
    # D3: Semantic Density
    "D3-01": "D3", "D3-02": "D3", "D3-03": "D3", "D3-04": "D3",
    # D4: Information Gain
    "D4-01": "D4", "D4-02": "D4", "D4-03": "D4", "D4-04": "D4",
    # D5: Multimodal & PR
    "D5-01": "D5", "D5-02": "D5", "D5-03": "D5", "D5-04": "D5",
    # D6: Audit
    "D6-01": "D6", "D6-02": "D6", "D6-03": "D6",
    # D7: Global Readiness (optional)
    "D7-01": "D7", "D7-02": "D7", "D7-03": "D7", "D7-04": "D7",
}

DOMAIN_WEIGHTS = {
    "D1": 20, "D2": 25, "D3": 15, "D4": 20, "D5": 10, "D6": 10
}

DOMAIN_WEIGHTS_GLOBAL = {
    "D1": 15, "D2": 20, "D3": 12, "D4": 18, "D5": 8, "D6": 7, "D7": 20
}

DOMAIN_LABELS = {
    "D1": "人 (Trust Graph)",
    "D2": "技術 (Extractability)",
    "D3": "技術 (Semantic Density)",
    "D4": "価値 (Information Gain)",
    "D5": "拡張 (Multimodal & PR)",
    "D6": "Audit (測定指標)",
    "D7": "グローバル (Global Readiness)",
}

DOMAIN_LABELS_SHORT = {
    "D1": "人", "D2": "抽出性", "D3": "接続性",
    "D4": "価値", "D5": "拡張", "D6": "計測",
    "D7": "グローバル"
}


def aggregate_scores(
    engine1_checks: list[dict],
    engine2_checks: list[dict] | None = None,
    manual_checks: dict[str, int] | None = None,
    global_mode: bool = False
) -> dict:
    """
    Engine 1/2の結果 + 手動チェックを集約し、6（or 7）領域スコアを算出。
    
    Args:
        engine1_checks: static_crawler.analyze_url()["checks"]
        engine2_checks: llm_analyzer.analyze_content_with_llm()["checks"]
        manual_checks: {"D1-01": 100, ...} 手動チェック結果
        global_mode: True の場合、D7 (Global Readiness) を含む7領域で評価
    """
    # 使用する重み付けを選択
    weights = DOMAIN_WEIGHTS_GLOBAL if global_mode else DOMAIN_WEIGHTS
    domain_ids = list(weights.keys())
    
    # 全項目のスコアを集約
    all_scores: dict[str, dict] = {}
    
    # Engine 1
    for check in (engine1_checks or []):
        all_scores[check["id"]] = check
    
    # Engine 2（上書き or 追加）
    for check in (engine2_checks or []):
        item_id = check["id"]
        if item_id in all_scores:
            e1_score = all_scores[item_id].get("score", 0)
            e2_score = check.get("score", 0)
            if e2_score > e1_score:
                all_scores[item_id] = check
            else:
                all_scores[item_id]["score"] = round((e1_score + e2_score) / 2)
                all_scores[item_id]["detail"] += f" | LLM判定: {check.get('detail', '')}"
        else:
            all_scores[item_id] = check
    
    # 手動チェック
    for item_id, score in (manual_checks or {}).items():
        if item_id not in all_scores:
            all_scores[item_id] = {"id": item_id, "score": score, "detail": "手動チェック"}
    
    # 領域ごとの集計
    domain_items: dict[str, list[int]] = {d: [] for d in domain_ids}
    for item_id, check in all_scores.items():
        domain = ITEM_TO_DOMAIN.get(item_id)
        if domain and domain in domain_items:
            domain_items[domain].append(check.get("score", 0))
    
    domain_scores = {}
    for domain, scores in domain_items.items():
        if scores:
            domain_scores[domain] = round(sum(scores) / len(scores))
        else:
            domain_scores[domain] = 0
    
    # 加重平均で総合スコア
    weighted_sum = sum(domain_scores.get(d, 0) * weights[d] for d in weights)
    total_weight = sum(weights.values())
    total_score = round(weighted_sum / total_weight)
    
    # レーダーチャートデータ（6角形 or 7角形）
    radar_data = [
        {"domain": DOMAIN_LABELS_SHORT[d], "domain_full": DOMAIN_LABELS[d], "score": domain_scores.get(d, 0)}
        for d in domain_ids
    ]
    
    # 改善優先度
    improvement_priorities = []
    for item_id, check in sorted(all_scores.items(), key=lambda x: x[1].get("score", 0)):
        # global_mode=Falseの時、D7項目はスキップ
        domain = ITEM_TO_DOMAIN.get(item_id)
        if not global_mode and domain == "D7":
            continue
        score = check.get("score", 0)
        if score < 60:
            improvement_priorities.append({
                "id": item_id,
                "score": score,
                "detail": check.get("detail", ""),
                "action": _get_improvement_action(item_id, score)
            })
    
    return {
        "domain_scores": domain_scores,
        "total_score": total_score,
        "radar_data": radar_data,
        "item_details": all_scores,
        "improvement_priorities": improvement_priorities[:10],
        "global_mode": global_mode
    }


def _get_improvement_action(item_id: str, score: int) -> str:
    """項目IDに応じた改善アクションを返す"""
    actions = {
        "D1-01": "LinkedIn投稿の専門領域を「AI × 特定産業」に絞り込んでください",
        "D1-02": "Schema.orgのsameAsプロパティでLinkedIn/GitHub等を紐付けてください",
        "D1-03": "専門家からのコメント・いいねを獲得する投稿戦略を実行してください",
        "D1-04": "投稿を「結論→箇条書き→洞察」の構造に統一してください",
        "D2-01": "robots.txtでGPTBotを制限し、OAI-SearchBotを許可してください",
        "D2-02": "ドメイン直下にllms.txtを設置してください（自動生成機能あり）",
        "D2-03": "<article>と<section>タグで本文をノイズから分離してください",
        "D2-04": "1段落300文字以内に分割し、冒頭に結論を配置してください",
        "D2-05": "JavaScriptなしでもコア情報が取得できるよう初期HTMLを改善してください",
        "D3-01": "JSON-LDでPerson/OrganizationとsameAsプロパティを設置してください",
        "D3-02": "significantLinkプロパティでPillar Contentを明示してください",
        "D3-03": "FAQPage/HowToスキーマを設置してください",
        "D3-04": "関連する専門用語・概念をもっと網羅してください",
        "D4-01": "独自のアンケートデータや導入事例の数値を記載してください",
        "D4-02": "一般論を避け、独自の対立構造や予測を提示してください",
        "D4-03": "「〇〇とは××である」の定義文を追加してください",
        "D4-04": "60日以内にコンテンツを更新し、<time>タグを設置してください",
        "D5-01": "画像にalt属性とfigcaptionで意図を説明してください",
        "D5-02": "動画にタイムスタンプ付き文字起こしを紐付けてください",
        "D5-03": "外部メディアで技術キーワードと自社名のセット言及を増やしてください",
        "D5-04": "権威ある外部ソースへの引用リンクを追加してください",
        "D6-01": "AIの回答での自社Citation Shareを定期計測してください",
        "D6-02": "AI回答内のセンチメント（推奨度）を監視してください",
        "D6-03": "サーバーログでAIボットの巡回頻度を確認してください",
        "D7-01": "LinkedIn等で英語での専門的な発信を開始してください",
        "D7-02": "hreflangタグとsameAsで日英エンティティを紐付けてください",
        "D7-03": "英語圏のAIエンジンでの引用実績を確認・構築してください",
        "D7-04": "機械翻訳ではなく、英語圏向けの独自インサイトを作成してください",
    }
    return actions.get(item_id, "改善が必要です")


def get_grade(total_score: int) -> tuple[str, str]:
    """総合スコアからグレードとラベルを返す"""
    if total_score >= 90:
        return "S", "AIの知識グラフ中枢に陣取っている"
    elif total_score >= 75:
        return "A", "引用確率 高"
    elif total_score >= 60:
        return "B", "引用確率 中（改善余地あり）"
    elif total_score >= 40:
        return "C", "引用確率 低（要改善）"
    else:
        return "D", "引用確率 極低（GEO対策が急務）"
