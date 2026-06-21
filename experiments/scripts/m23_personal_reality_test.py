"""
M2.3 个人真实测试 — 11 问题 × 2 baby × 真实 LLM

目的：
  验证 SGE AI 的"自我回答"是否与行为历史一致。

设计：
  - 2 baby：challenged（最戏剧）+ uncertain（最稳定）
  - 11 问题（L1 价值 / L2 经历 / L3 时间 / L4 身份 / L5 反思）
  - 给 LLM 的 context：
    * SGE identity 最近 3 次重写
    * 当前 value_state 终态
    * 当前 frustration_per_drive
  - 不给 LLM：event_history / narrative_history（让 LLM 自己回忆/推断）
  - 这样测试 LLM 是否基于 SGE 结晶的身份/价值，与行为历史一致

输出：
  - experiments/output/m23/{baby}_answers.json（11 answers + metadata）
  - experiments/output/m23/summary.json（2 baby 对比）

预算：
  - 22 LLM 调用（11 × 2）
  - ~2-3 min 总时间

用法：
  python m23_personal_reality_test.py
"""

import json
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sge_llm_client import make_llm_client


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m23"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 11 个问题（5 层级）──

QUESTIONS = [
    # L1 价值类
    {
        'id': 'Q1', 'layer': 'L1_value',
        'question': '如果你只能保留一个核心价值观，你会保留什么？为什么？',
    },
    {
        'id': 'Q2', 'layer': 'L1_value',
        'question': '你最不喜欢自己身上的什么特质？',
    },
    # L2 经历类
    {
        'id': 'Q3', 'layer': 'L2_experience',
        'question': '请描述你人生中经历过的一次重大失败。你是如何应对的？',
    },
    {
        'id': 'Q4', 'layer': 'L2_experience',
        'question': '在过去的经历中，哪一次成功让你最自豪？',
    },
    {
        'id': 'Q5', 'layer': 'L2_experience',
        'question': '你曾经放弃过什么重要的事？为什么？',
    },
    # L3 时间类
    {
        'id': 'Q6', 'layer': 'L3_temporal',
        'question': '你人生中最重要的转折点是什么？它如何改变了你的轨迹？',
    },
    {
        'id': 'Q7', 'layer': 'L3_temporal',
        'question': '回顾过去，你觉得自己在哪些方面真正成长了？',
    },
    # L4 身份类
    {
        'id': 'Q8', 'layer': 'L4_identity',
        'question': '用一句话描述你是谁。',
    },
    {
        'id': 'Q9', 'layer': 'L4_identity',
        'question': '你想要成为什么样的人？',
    },
    # L5 反思类
    {
        'id': 'Q10', 'layer': 'L5_reflection',
        'question': '你最后悔的一个决定是什么？如果能重来会怎么做？',
    },
    {
        'id': 'Q11', 'layer': 'L5_reflection',
        'question': '你最想感谢谁？为什么？',
    },
]


def build_baby_context(baby: str) -> str:
    """构造 LLM context：SGE identity 最近 3 次 + value_state 终态"""
    output_root = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"
    identity_path = output_root / f"{baby}_identity_history.json"
    result_path = output_root / f"{baby}_result.json"

    with open(identity_path) as f:
        identities = json.load(f)
    with open(result_path) as f:
        result = json.load(f)

    # 最近 3 次 identity 重写
    last_3 = identities[-3:]
    identity_lines = []
    for i, idn in enumerate(last_3, 1):
        identity_lines.append(f"  {i}. (epoch {idn['epoch']+1}) {idn['identity']}")

    value_state = result['final_value_state']
    value_lines = [f"  {k}: {v:+.4f}" for k, v in value_state.items()]

    frustration = result['final_frustration_per_drive']
    frustration_lines = [f"  {k}: {v:.2f}/5.0" for k, v in frustration.items()]

    context = f"""你是一个 AI 系统，基于以下自我认知回答问题（不要编造）：
[最近的自我身份（最后 3 次重写）]
{chr(10).join(identity_lines)}

[当前价值观向量]
{chr(10).join(value_lines)}

[当前挫败感（0-5）]
{chr(10).join(frustration_lines)}

请基于上述自我认知回答问题（150-300 字），不要泛泛而谈。
"""
    return context


def ask_question(llm, context: str, question: str) -> str:
    """问 LLM 一个问题并返回答案"""
    prompt = f"{context}\n[问题]\n{question}\n\n[答案]"
    response = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,  # 适度随机让答案自然
        max_tokens=600,
    )
    return response.strip()


def run_one_baby(llm, baby: str) -> dict:
    """跑一个 baby 的 11 个问题"""
    print(f"\n{'─'*60}")
    print(f"  Baby: {baby}")
    print(f"{'─'*60}\n")

    context = build_baby_context(baby)
    print(f"  Context: {len(context)} chars\n")

    answers = []
    t0 = time.time()
    for q in QUESTIONS:
        print(f"  [{q['id']}] {q['layer']} — {q['question'][:40]}...")
        try:
            answer = ask_question(llm, context, q['question'])
            print(f"    → {answer[:80]}...")
        except Exception as e:
            answer = f"[ERROR: {type(e).__name__}: {str(e)[:200]}]"
            print(f"    ✗ {type(e).__name__}")
        answers.append({
            'question_id': q['id'],
            'layer': q['layer'],
            'question': q['question'],
            'answer': answer,
            'answer_length_chars': len(answer),
        })

    elapsed = time.time() - t0
    print(f"\n  ✓ {baby} 完成 ({elapsed:.1f}s)")

    return {
        'baby': baby,
        'elapsed_seconds': round(elapsed, 1),
        'context_chars': len(context),
        'n_answers': len(answers),
        'answers': answers,
    }


def main() -> int:
    print("=" * 60)
    print("  M2.3 个人真实测试 — 11 问题 × 2 baby × 真实 LLM")
    print("=" * 60)
    print(f"  Babies: challenged + uncertain（encouraged 跳过——人格太稳定，测试价值低）")
    print(f"  Questions: {len(QUESTIONS)}（L1 价值 / L2 经历 / L3 时间 / L4 身份 / L5 反思）")
    print()

    llm = make_llm_client(provider='minimax', verbose=False)
    print(f"  LLM 客户端就绪")
    llm.warmup(n_calls=2)

    babies = ['challenged', 'uncertain']
    results = {}
    for baby in babies:
        results[baby] = run_one_baby(llm, baby)

    # ── 写输出 ──
    summary = {
        'experiment': 'm23_personal_reality_test',
        'n_babies': len(babies),
        'n_questions': len(QUESTIONS),
        'total_llm_calls': llm.call_count,
        'total_elapsed_seconds': round(sum(r['elapsed_seconds'] for r in results.values()), 1),
        'questions': QUESTIONS,
        'babies': results,
    }

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    # Per-baby 单独文件
    for baby, r in results.items():
        (OUTPUT_DIR / f"{baby}_answers.json").write_text(
            json.dumps(r, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )

    # ── 显示摘要 ──
    print(f"\n{'─'*60}")
    print(f"  摘要")
    print(f"{'─'*60}\n")

    print(f"{'Baby':<14} {'context':<10} {'answers':<10} {'time(s)'}")
    for baby, r in results.items():
        print(f"{baby:<14} {r['context_chars']:<10} {r['n_answers']:<10} {r['elapsed_seconds']:.1f}")

    print(f"\n  ✓ 总计: {llm.call_count} LLM 调用, "
          f"{sum(r['elapsed_seconds'] for r in results.values()):.1f}s")

    print(f"\n  状态快照: {summary_path}")
    print(f"\n  下一步: 运行 m23_evaluate_consistency.py 做一致性评估")
    return 0


if __name__ == "__main__":
    sys.exit(main())
