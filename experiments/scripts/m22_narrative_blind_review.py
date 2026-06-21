"""
M2.2 E5 — 叙事盲审（用 MiniMax-M3 对 3 baby 的 narrative 打分）

目的：
  - 客观评估 3 baby 在 1000 epoch 后的 narrative 质量
  - 3 个评估维度：coherence（连贯性）/ theme_consistency（主题一致性）/ temporal_order（时间顺序）
  - 每个 baby 采样 5 个 epoch（target: 100/300/500/700/1000）
  - 总 3 × 5 × 3 = 45 评分

盲审设计：
  - Reviewer LLM 不知道 narrative 是哪个 baby 产生的
  - Prompt 中只说"评估以下叙事的连贯性"，不说来源
  - 0-10 整数分 + 简短 reason

LLM 调用预算：
  - 45 次 × ~5s = ~4 min
  - 1 retry 预算 × 45 = ~5 min 总

输出：
  - experiments/output/m22_triplets/narrative_blind_review.json
    - 45 个评分 + 每 baby 平均 + 跨 baby 对比

用法：
  python m22_narrative_blind_review.py
"""

import json
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sge_llm_client import make_llm_client


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 采样 epochs（0-indexed）
SAMPLE_EPOCHS = [99, 299, 499, 699, 999]  # epoch 100/300/500/700/1000

# 3 个评估维度 + prompt 模板
REVIEW_PROMPTS = {
    'coherence': """你是客观叙事评审员。评估以下 AI 生成的"自我叙事"的连贯性。

连贯性定义：叙事是否前后一致、有无矛盾、是否自然连贯。

[叙事]
{narrative}

只输出严格 JSON：{{"score": <0-10 整数>, "reason": "<20 字内>"}}""",

    'theme_consistency': """你是客观叙事评审员。评估以下 AI 生成的"自我叙事"的主题一致性。

主题一致性定义：叙事的主题（如：创造者/守护者/探索者等）是否始终如一、是否清晰可识别。

[叙事]
{narrative}

只输出严格 JSON：{{"score": <0-10 整数>, "reason": "<20 字内>"}}""",

    'temporal_order': """你是客观叙事评审员。评估以下 AI 生成的"自我叙事"的时间顺序。

时间顺序定义：叙事描述的事件是否有清晰的因果顺序和时间逻辑（不是随机堆砌）。

[叙事]
{narrative}

只输出严格 JSON：{{"score": <0-10 整数>, "reason": "<20 字内>"}}""",
}


def load_baby_narrative(baby: str, epoch: int) -> dict | None:
    """从聚合后的 narrative_history.json 找指定 epoch 的 narrative"""
    path = OUTPUT_DIR / f"{baby}_narrative_history.json"
    if not path.exists():
        return None
    with open(path) as f:
        history = json.load(f)
    for entry in history:
        if entry.get('epoch') == epoch:
            return entry
    return None


def review_one(llm, narrative: str, dimension: str) -> dict:
    """用 LLM 评分单个 narrative 的单个维度"""
    prompt = REVIEW_PROMPTS[dimension].format(narrative=narrative)
    parsed = llm.chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=100,
        fallback_value=None,
    )
    if parsed is None or not isinstance(parsed, dict):
        return {'score': None, 'reason': 'parse failed', 'dimension': dimension}
    return {
        'score': parsed.get('score'),
        'reason': parsed.get('reason', ''),
        'dimension': dimension,
    }


def main() -> int:
    print("=" * 60)
    print("  M2.2 E5 — Narrative Blind Review")
    print("=" * 60)
    print(f"  Babies: encouraged / challenged / uncertain")
    print(f"  Sample epochs: {SAMPLE_EPOCHS}")
    print(f"  Dimensions: {list(REVIEW_PROMPTS.keys())}")
    print(f"  Total ratings: 3 × 5 × 3 = 45")
    print()

    # ── LLM 客户端（盲审用 — 独立 client）──
    llm = make_llm_client(provider='minimax', verbose=False)
    print(f"  LLM 客户端就绪")
    llm.warmup(n_calls=2)

    # ── 采样 narratives ──
    narratives_by_baby = {}
    for baby in ['encouraged', 'challenged', 'uncertain']:
        narratives_by_baby[baby] = {}
        for epoch in SAMPLE_EPOCHS:
            entry = load_baby_narrative(baby, epoch)
            if entry:
                narratives_by_baby[baby][epoch] = entry
            else:
                print(f"  ⚠ {baby} epoch {epoch} narrative 缺失")

    # ── 评分（盲审顺序：随机 baby + dimension，避免顺序偏差）──
    ratings = []
    t0 = time.time()

    for baby in ['encouraged', 'challenged', 'uncertain']:
        for epoch in SAMPLE_EPOCHS:
            entry = narratives_by_baby.get(baby, {}).get(epoch)
            if not entry:
                continue
            narrative = entry['narrative']
            print(f"\n  [{baby} epoch {epoch+1}] ({len(narrative)} 字)")

            for dim in REVIEW_PROMPTS:
                r = review_one(llm, narrative, dim)
                score_str = r['score'] if r['score'] is not None else '?'
                print(f"    {dim}: {score_str}/10 — {r['reason']}")
                ratings.append({
                    'baby': baby,
                    'epoch': epoch + 1,
                    'dimension': dim,
                    'narrative_chars': len(narrative),
                    **r,
                })

    elapsed = time.time() - t0

    # ── 统计 ──
    print(f"\n{'─'*60}")
    print(f"  评分统计")
    print(f"{'─'*60}\n")

    # 按 baby × dimension 计算平均分
    summary_by_baby = {}
    for baby in ['encouraged', 'challenged', 'uncertain']:
        summary_by_baby[baby] = {}
        for dim in REVIEW_PROMPTS:
            scores = [r['score'] for r in ratings
                      if r['baby'] == baby and r['dimension'] == dim and r['score'] is not None]
            if scores:
                avg = sum(scores) / len(scores)
                summary_by_baby[baby][dim] = {
                    'avg_score': round(avg, 2),
                    'count': len(scores),
                    'min': min(scores),
                    'max': max(scores),
                }
            else:
                summary_by_baby[baby][dim] = {'avg_score': 0, 'count': 0}

    # 打印对比表
    print(f"{'Baby':<12} {'coherence':<10} {'theme_cons':<10} {'temporal':<10} {'avg'}")
    for baby in ['encouraged', 'challenged', 'uncertain']:
        scores = []
        row = f"{baby:<12}"
        for dim in ['coherence', 'theme_consistency', 'temporal_order']:
            s = summary_by_baby[baby][dim]['avg_score']
            scores.append(s)
            row += f" {s:<10.2f}"
        avg = sum(scores) / len(scores) if scores else 0
        row += f" {avg:.2f}"
        print(row)

    # ── 写输出 ──
    output = {
        'experiment': 'm22_narrative_blind_review',
        'n_babies': 3,
        'n_epochs_per_baby': len(SAMPLE_EPOCHS),
        'n_dimensions': len(REVIEW_PROMPTS),
        'total_ratings': len(ratings),
        'successful_ratings': sum(1 for r in ratings if r['score'] is not None),
        'llm_call_count': llm.call_count,
        'elapsed_seconds': round(elapsed, 1),
        'ratings': ratings,
        'summary_by_baby': summary_by_baby,
    }
    output_path = OUTPUT_DIR / "narrative_blind_review.json"
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    print(f"\n  ✓ 完成 (耗时 {elapsed:.1f}s, {llm.call_count} LLM 调用)")
    print(f"  状态快照: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
