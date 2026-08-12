"""生成 Alice 200 事件 fixture（K12 真实模式）。

设计依据：research/phase3/90-applications/student-digital-twin.md §5.1
  - events 1-80: math/algebra 反复失败（78 → 45，frustration 累积）
  - events 81-120: english 稳定上升（75 → 88）
  - events 121-160: emotional_event 穿插
  - events 161-180: struggle_breakthrough（algebra 45 → 65）
  - events 181-200: math/algebra 巩固期（稳定 70 左右）

事件类型分布（共 200）：
  - mastery_drop:           30 个（math 失败 / english 偶尔失利）
  - mastery_rise:           30 个（math 反弹 / english 上升 / breakthrough）
  - struggle_breakthrough:  10 个（algebra 开窍期）
  - emotional_event:        50 个（和家长 / 朋友 / 老师）
  - social_event:           30 个（朋友 / 同学互动）
  - fatigue_event:          20 个（睡眠 / 疲劳）
  - praise_event:           15 个（被老师 / 家长表扬）
  - criticism_event:        15 个（被批评）
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# ══════════════════════════════════════════════
# Alice 的状态轨迹（手工设计的"剧本"）
# ══════════════════════════════════════════════
#
# 每个时间点 Alice 的 mastery（按学科×主题）
# 时间轴：8 周（每 epoch ≈ 半天），共 200 epoch

# 格式：[(week, math_algebra, math_geometry, english_reading, english_writing, science)]
MATH_ALGEBRA_TRAJECTORY = [
    # Week 1-2: 反复失败
    (1, 78), (2, 72), (3, 65), (4, 58),
    # Week 3-4: 跌至谷底
    (5, 52), (6, 48), (7, 45), (8, 46),
    # Week 5: breakthrough
    (9, 50), (10, 58), (11, 65),
    # Week 6-8: 巩固
    (12, 68), (13, 70), (14, 70), (15, 71), (16, 70),
]


def _interpolate_math_algebra(event_idx: int) -> float:
    """根据 event_idx（0-199）插值返回当前 algebra mastery。"""
    week = event_idx / 25 + 1  # 200 events / 8 weeks
    # 找最近的两个 trajectory 点
    sorted_pts = sorted(MATH_ALGEBRA_TRAJECTORY)
    for i in range(len(sorted_pts) - 1):
        w1, v1 = sorted_pts[i]
        w2, v2 = sorted_pts[i + 1]
        if w1 <= week <= w2:
            t = (week - w1) / (w2 - w1)
            return v1 + (v2 - v1) * t
    return sorted_pts[-1][1]


def _interpolate_english_reading(event_idx: int) -> float:
    """English reading 稳定上升 75 → 88。"""
    return 75 + (88 - 75) * (event_idx / 199)


def _interpolate_english_writing(event_idx: int) -> float:
    """English writing 稳定上升 80 → 92。"""
    return 80 + (92 - 80) * (event_idx / 199)


def _interpolate_math_geometry(event_idx: int) -> float:
    """Math geometry 稳定 70-80（无大波动）。"""
    return 70 + (80 - 70) * (event_idx / 199) + random.uniform(-2, 2)


def _interpolate_science(event_idx: int) -> float:
    """Science 稳定 72-85。"""
    return 72 + (85 - 72) * (event_idx / 199) + random.uniform(-2, 2)


# ══════════════════════════════════════════════
# 事件描述模板（按 event_type）
# ══════════════════════════════════════════════

EVENT_TEMPLATES = {
    'mastery_drop': {
        'math/algebra': [
            '一元一次方程小测：3/10 错',
            '因式分解作业 5 道错 4 道',
            '二元一次方程组测验：基础题失分',
            '代数应用题：找不到等量关系',
            '期中模拟考：代数部分 35/100',
            '一元二次方程根的判别式混淆',
            '代数式化简：同类项合并错误',
        ],
        'math/geometry': [
            '三角形面积计算公式混淆',
            '圆周率近似值用错',
        ],
        'english/reading': [
            '阅读理解：主旨题答错',
        ],
    },
    'mastery_rise': {
        'math/algebra': [
            '一元一次方程小测：8/10 正确',
            '因式分解作业正确率提升',
            '回家作业全对',
            '课堂小测满分',
        ],
        'english/reading': [
            '阅读理解 5 道对 4 道',
            '长难句分析准确率提升',
            '生词本复习效果好',
        ],
        'english/writing': [
            '作文被老师当范文朗读',
            '段落结构清晰',
        ],
    },
    'struggle_breakthrough': {
        'math/algebra': [
            '突然理解十字相乘法原理',
            '一元二次方程求根公式融会贯通',
            '应用题"设未知数"思路打通',
            '因式分解"提取公因式"开窍',
            '配方法完全掌握',
        ],
    },
    'emotional_event': {
        'general': [
            '和妈妈因为数学成绩吵架',
            '爸爸说"女孩子学不好数学"',
            '考试前焦虑失眠',
            '因为成绩下滑哭了一场',
            '老师主动谈话鼓励',
            '和好朋友倾诉心事',
            '看了一部励志电影',
            '得到心理咨询师支持',
            '妈妈道歉并道歉',
            '爸爸开始陪写作业',
            '和姐姐聊学习压力',
            '收到亲戚的关心',
        ],
    },
    'social_event': {
        'general': [
            '和新同学成为朋友',
            '和好朋友一起做作业',
            '和同桌讨论数学题',
            '参加班级读书会',
            '社团活动认识新朋友',
            '和邻居家孩子一起玩',
            '和同学一起吃午饭',
            '加入数学兴趣小组',
            '和好朋友分享零食',
            '邀请同学来家里玩',
        ],
    },
    'fatigue_event': {
        'general': [
            '昨晚只睡了 5 小时',
            '熬夜写作业',
            '周末补课太多很累',
            '下午体育课后疲劳',
            '感冒发烧',
            '头疼请假',
            '中午没午休',
        ],
    },
    'praise_event': {
        'general': [
            '老师当堂表扬作文写得好',
            '数学老师点名说"有进步"',
            '家长会上被表扬',
            '得到校长嘉许',
            '作文比赛获奖',
            '朗读比赛第一名',
            '被评为"进步之星"',
            '妈妈夸"最近很努力"',
        ],
    },
    'criticism_event': {
        'general': [
            '被老师批评"上课走神"',
            '被妈妈说"不够努力"',
            '和同学吵架被老师调解',
            '作业潦草被退回',
            '上课迟到被批评',
            '被爸爸说"考不上好高中"',
        ],
    },
}


def _template_for(event_type: str, subject: str, topic: str | None) -> str:
    """从模板池随机选一条描述。"""
    type_pool = EVENT_TEMPLATES.get(event_type, {})
    # 优先按 subject/topic 匹配
    if subject and topic:
        subj_topic_pool = type_pool.get(f"{subject}/{topic}", [])
        if subj_topic_pool:
            return random.choice(subj_topic_pool)
    if subject:
        for k, v in type_pool.items():
            if k.startswith(f"{subject}/"):
                return random.choice(v)
    general_pool = type_pool.get('general', [])
    if general_pool:
        return random.choice(general_pool)
    return f"{event_type} event ({subject}/{topic})"


def _emotion_for(event_type: str, mastery_delta: float) -> tuple[str, float]:
    """根据事件类型 + mastery 变化返回（emotion, intensity）。"""
    if event_type == 'mastery_drop':
        if mastery_delta <= -15:
            return random.choice([('frustrated', 0.8), ('devastated', 0.9), ('anxious', 0.7)])
        elif mastery_delta <= -8:
            return random.choice([('frustrated', 0.5), ('discouraged', 0.6), ('anxious', 0.5)])
        else:
            return random.choice([('slightly_disappointed', 0.3), ('concerned', 0.4)])
    elif event_type == 'mastery_rise':
        if mastery_delta >= 8:
            return random.choice([('proud', 0.7), ('relieved', 0.6), ('confident', 0.7)])
        else:
            return random.choice([('pleased', 0.4), ('satisfied', 0.5)])
    elif event_type == 'struggle_breakthrough':
        return random.choice([('eureka', 0.9), ('excited', 0.8), ('relieved', 0.7), ('proud', 0.8)])
    elif event_type == 'emotional_event':
        return random.choice([('anxious', 0.6), ('sad', 0.5), ('angry', 0.6), ('overwhelmed', 0.7)])
    elif event_type == 'social_event':
        return random.choice([('happy', 0.6), ('connected', 0.5), ('included', 0.5)])
    elif event_type == 'fatigue_event':
        return random.choice([('tired', 0.7), ('exhausted', 0.8), ('drained', 0.6)])
    elif event_type == 'praise_event':
        return random.choice([('proud', 0.7), ('happy', 0.6), ('motivated', 0.6)])
    elif event_type == 'criticism_event':
        return random.choice([('embarrassed', 0.5), ('defensive', 0.6), ('sad', 0.5)])
    return ('neutral', 0.0)


# ══════════════════════════════════════════════
# 主生成逻辑
# ══════════════════════════════════════════════


def generate_alice_200_events(seed: int = 42) -> list[dict]:
    """生成 Alice 200 事件列表（按 §5.1 设计的事件分布）。

    关键设计：mastery_drop / mastery_rise 强制 delta 方向（与 event_type 一致），
    breakthrough 强制显著上升，确保轨迹单调 + 符合 Alice "math 反复失败 → 突破" 故事弧。
    """
    random.seed(seed)

    events = []
    last_mastery = {
        ('math', 'algebra'): 78.0,
        ('math', 'geometry'): 75.0,
        ('english', 'reading'): 75.0,
        ('english', 'writing'): 80.0,
        ('science', 'general'): 72.0,
    }

    base_time = datetime(2026, 5, 1, 8, 0, 0)

    for i in range(200):
        # 1. 决定本事件类型 + 学科主题（按分布）
        if i < 80:  # Week 1-3.2: math 反复失败期
            event_type = random.choices(
                ['mastery_drop', 'mastery_rise', 'emotional_event', 'fatigue_event', 'criticism_event'],
                weights=[55, 8, 18, 10, 9],
            )[0]
            subject, topic = 'math', 'algebra'
        elif i < 120:  # Week 3.2-4.8: english 上升期
            event_type = random.choices(
                ['mastery_rise', 'mastery_drop', 'social_event', 'praise_event', 'emotional_event'],
                weights=[50, 8, 18, 14, 10],
            )[0]
            if random.random() < 0.7:
                subject, topic = 'english', 'reading'
            else:
                subject, topic = 'english', 'writing'
        elif i < 160:  # Week 4.8-6.4: emotional 主导
            event_type = random.choices(
                ['emotional_event', 'social_event', 'praise_event', 'criticism_event', 'fatigue_event'],
                weights=[40, 25, 15, 10, 10],
            )[0]
            subject, topic = None, None
        elif i < 180:  # Week 6.4-7.2: breakthrough
            event_type = random.choices(
                ['struggle_breakthrough', 'mastery_rise', 'praise_event', 'emotional_event'],
                weights=[50, 25, 15, 10],
            )[0]
            subject, topic = 'math', 'algebra'
        else:  # Week 7.2-8: 巩固
            event_type = random.choices(
                ['mastery_rise', 'mastery_drop', 'praise_event', 'social_event', 'emotional_event'],
                weights=[25, 15, 25, 20, 15],
            )[0]
            if random.random() < 0.6:
                subject, topic = 'math', 'algebra'
            else:
                subject, topic = random.choice([
                    ('math', 'geometry'),
                    ('english', 'reading'),
                    ('science', 'general'),
                ])

        # 2. 计算 mastery_after（强制 delta 方向）
        if subject and topic:
            key = (subject, topic)
            if key not in last_mastery:
                last_mastery[key] = 75.0
            mastery_before = last_mastery[key]

            if event_type == 'mastery_drop':
                # 强制负 delta，限制下限 35（避免触底 0）
                delta = -random.uniform(3, 12)
                mastery_after = max(35, mastery_before + delta)
            elif event_type == 'mastery_rise':
                # 强制正 delta，限制上限 90（避免触顶 100）
                delta = random.uniform(3, 10)
                mastery_after = min(90, mastery_before + delta)
            elif event_type == 'struggle_breakthrough':
                # 显著上升，限制上限 80
                delta = random.uniform(8, 15)
                mastery_after = min(80, mastery_before + delta)
            else:
                # emotional / social / fatigue / praise / criticism → 小波动
                delta = random.uniform(-2, 2)
                mastery_after = max(0, min(100, mastery_before + delta))

            last_mastery[key] = mastery_after
        else:
            mastery_before = 0.0
            mastery_after = 0.0
            delta = 0.0

        # 3. 情绪
        emotion, intensity = _emotion_for(event_type, delta)

        # 4. 描述
        description = _template_for(event_type, subject, topic)

        # 5. 时间戳
        timestamp = base_time + timedelta(hours=i * 12)

        event = {
            'event_id': f'evt_alice_{i+1:03d}',
            'event_type': event_type,
            'subject': subject,
            'topic': topic,
            'mastery_before': round(mastery_before, 1),
            'mastery_after': round(mastery_after, 1),
            'mastery_delta': round(delta, 1),
            'emotion': emotion,
            'emotion_intensity': round(intensity, 2),
            'description': description,
            'timestamp': timestamp.isoformat(),
        }
        events.append(event)

    return events


def main():
    """生成 fixture 并写到 fixtures/alice_200_events.jsonl"""
    events = generate_alice_200_events(seed=42)
    output_path = Path(__file__).parent / 'alice_200_events.jsonl'
    with open(output_path, 'w', encoding='utf-8') as f:
        for evt in events:
            f.write(json.dumps(evt, ensure_ascii=False) + '\n')

    # 简单统计
    from collections import Counter
    type_counts = Counter(e['event_type'] for e in events)
    print(f'✓ 已生成 {len(events)} 个事件 → {output_path}')
    print('事件类型分布:')
    for et, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f'  {et:25s} {cnt:3d}')

    # mastery 轨迹概览
    print('\nmastery 轨迹概览:')
    for subj_topic in [('math', 'algebra'), ('math', 'geometry'),
                       ('english', 'reading'), ('english', 'writing')]:
        scores = [e['mastery_after'] for e in events
                  if e['subject'] == subj_topic[0] and e['topic'] == subj_topic[1]]
        if scores:
            label = f"{subj_topic[0]}/{subj_topic[1]}"
            print(f'  {label:25s} {min(scores):5.1f} → {max(scores):5.1f} (终值 {scores[-1]:5.1f})')


if __name__ == '__main__':
    main()