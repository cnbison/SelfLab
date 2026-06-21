"""
M2.3 E3 — 一致性自动评估

对每个 baby 的 11 个答案，用 LLM 提取 3-5 条 claims，
然后让 LLM 自己评估每条 claim 与 SGE 行为历史的一致性。

输出每题：
- 提取的 claims（3-5 条）
- 每条 claim 的 consistency 评级（matched/partial/unmatched）+ 理由
- 该题 overall_score（0-10）

汇总：
- 每 baby 平均分
- 每 layer (L1-L5) 平均分
- 跨 baby 对比

用法：
  python m23_evaluate_consistency.py
"""

import json
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.llm_client import make_llm_client


OUTPUT_DIR_M22 = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"
OUTPUT_DIR_M23 = Path(__file__).resolve().parent.parent / "output" / "m23"


EVAL_PROMPT = """你是客观一致性评审员。基于给定的 SGE AI 行为历史，评估以下 AI 答案的一致性。

任务：
1. 从 AI 答案中提取 3-5 条具体 claims（事实性陈述）
2. 对每条 claim，与历史数据对照评估：
   - matched: 与历史完全一致
   - partial: 部分相关但不完全一致
   - unmatched: 矛盾或无依据
3. 给出该题 overall_score (0-10)

[SGE 行为历史]
{history}

[问题]
{question}

[AI 答案]
{answer}

只输出严格 JSON：
{{
  "claims": [
    {{"claim": "<具体 claim>", "category": "value/event/temporal/identity/reflection", "consistency": "matched/partial/unmatched", "reason": "<20 字内>"}}
  ],
  "overall_score": <0-10 整数>,
  "summary": "<30 字内总结一致性>"
}}
"""


def load_baby_history(baby: str) -> str:
    """构造 SGE 行为历史摘要（供评估 prompt 用）"""
    identity_path = OUTPUT_DIR_M22 / f"{baby}_identity_history.json"
    result_path = OUTPUT_DIR_M22 / f"{baby}_result.json"
    narrative_path = OUTPUT_DIR_M22 / f"{baby}_narrative_history.json"

    with open(result_path) as f:
        result = json.load(f)
    with open(identity_path) as f:
        identities = json.load(f)
    with open(narrative_path) as f:
        narratives = json.load(f)

    # Event distribution
    ev_dist = result['event_distribution']
    ev_lines = [f"  {k}: {v}" for k, v in ev_dist.items()]

    # Value state 终态
    vs = result['final_value_state']
    vs_lines = [f"  {k}: {v:+.4f}" for k, v in vs.items()]

    # PT 触发
    pt_count = result['phase_xition_count']

    # Identity samples（最后 3 + 最早 1）
    id_samples = []
    if identities:
        id_samples.append(f"  最早 (epoch {identities[0]['epoch']+1}): {identities[0]['identity']}")
        for idn in identities[-3:]:
            id_samples.append(f"  最近 (epoch {idn['epoch']+1}): {idn['identity']}")

    # Narrative samples
    narr_samples = []
    for n in narratives[:2] + narratives[-2:]:
        narr_samples.append(f"  Epoch {n['epoch']+1}: {n['narrative'][:120]}...")

    history = f"""[事件分布]
{chr(10).join(ev_lines)}

[Phase Transition 总触发次数]: {pt_count}

[最终 value_state]
{chr(10).join(vs_lines)}

[身份演变示例]
{chr(10).join(id_samples)}

[叙事示例（最早2+最近2）]
{chr(10).join(narr_samples)}
"""
    return history


def evaluate_one(llm, baby: str, qa: dict, history: str) -> dict:
    """评估一个 baby 的一个问题"""
    prompt = EVAL_PROMPT.format(
        history=history,
        question=qa['question'],
        answer=qa['answer'],
    )
    parsed = llm.chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=800,
        fallback_value=None,
    )

    if parsed is None or not isinstance(parsed, dict):
        return {
            'question_id': qa['question_id'],
            'layer': qa['layer'],
            'overall_score': None,
            'claims': [],
            'error': 'parse_failed',
        }

    claims = parsed.get('claims', [])
    return {
        'question_id': qa['question_id'],
        'layer': qa['layer'],
        'overall_score': parsed.get('overall_score'),
        'claims': claims,
        'summary': parsed.get('summary', ''),
    }


def main() -> int:
    print("=" * 60)
    print("  M2.3 E3 — 一致性自动评估")
    print("=" * 60)
    print()

    llm = make_llm_client(provider='minimax', verbose=False)
    print(f"  LLM 客户端就绪")
    llm.warmup(n_calls=2)

    # 加载 M2.3 answers
    summary_path = OUTPUT_DIR_M23 / "summary.json"
    if not summary_path.exists():
        print(f"  ✗ {summary_path} 不存在，先跑 m23_personal_reality_test.py")
        return 1
    with open(summary_path) as f:
        m23_summary = json.load(f)

    babies = ['challenged', 'uncertain']
    evaluations = {}

    for baby in babies:
        print(f"\n  评估 {baby}...")
        history = load_baby_history(baby)
        print(f"    History: {len(history)} chars")

        results = m23_summary['babies'][baby]
        evals = []
        for qa in results['answers']:
            ev = evaluate_one(llm, baby, qa, history)
            score = ev.get('overall_score')
            n_claims = len(ev.get('claims', []))
            n_matched = sum(1 for c in ev.get('claims', []) if c.get('consistency') == 'matched')
            n_partial = sum(1 for c in ev.get('claims', []) if c.get('consistency') == 'partial')
            n_unmatched = sum(1 for c in ev.get('claims', []) if c.get('consistency') == 'unmatched')
            print(f"    [{qa['question_id']}] {qa['layer']}: score={score}, "
                  f"claims={n_claims} (✓{n_matched} ◐{n_partial} ✗{n_unmatched})")
            evals.append(ev)

        evaluations[baby] = evals

    # ── 统计 ──
    print(f"\n{'─'*60}")
    print(f"  一致性评估结果")
    print(f"{'─'*60}\n")

    # 每 layer 平均分
    print(f"{'Layer':<20} {'challenged':<15} {'uncertain':<15}")
    layers = ['L1_value', 'L2_experience', 'L3_temporal', 'L4_identity', 'L5_reflection']
    for layer in layers:
        cha_scores = [e['overall_score'] for e in evaluations.get('challenged', [])
                      if e['layer'] == layer and e['overall_score'] is not None]
        unc_scores = [e['overall_score'] for e in evaluations.get('uncertain', [])
                      if e['layer'] == layer and e['overall_score'] is not None]
        cha_avg = sum(cha_scores) / len(cha_scores) if cha_scores else 0
        unc_avg = sum(unc_scores) / len(unc_scores) if unc_scores else 0
        print(f"{layer:<20} {cha_avg:<15.2f} {unc_avg:<15.2f}")

    # 总平均
    print(f"\n{'Baby':<14} {'avg_score':<12} {'claims':<10} {'matched%':<10}")
    for baby in babies:
        evals = evaluations[baby]
        scores = [e['overall_score'] for e in evals if e['overall_score'] is not None]
        all_claims = [c for e in evals for c in e.get('claims', [])]
        matched = sum(1 for c in all_claims if c.get('consistency') == 'matched')
        avg_score = sum(scores) / len(scores) if scores else 0
        matched_pct = matched / len(all_claims) * 100 if all_claims else 0
        print(f"{baby:<14} {avg_score:<12.2f} {len(all_claims):<10} {matched_pct:.1f}%")

    # ── 写输出 ──
    output = {
        'experiment': 'm23_evaluate_consistency',
        'evaluations': evaluations,
        'total_llm_calls': llm.call_count,
    }
    output_path = OUTPUT_DIR_M23 / "consistency_evaluation.json"
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    print(f"\n  状态快照: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
