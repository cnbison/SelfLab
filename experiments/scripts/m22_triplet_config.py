"""
M2.2 triplet 配置加载器

从 m22_{encouraged,challenged,uncertain}.yaml 加载 EventGenerator 构造参数：
- baby_id
- value_conflict_prob
- distribution_by_epoch

用法：
    cfg = load_triplet_config('experiments/configs/m22_encouraged.yaml')
    event_gen = EventGenerator(
        baby_id=cfg['baby_id'],
        seed=42,
        value_conflict_prob=cfg['value_conflict_prob'],
        distribution_by_epoch=cfg['distribution_by_epoch'],
    )

关联：[SGE-M22-Implementation-Plan.md §E2](../research/sge-feasibility/SGE-M22-Implementation-Plan.md#e2三胞胎事件流配置3-个-yaml)
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any


def load_triplet_config(yaml_path: str | Path) -> Dict[str, Any]:
    """加载 triplet yaml 并提取 EventGenerator 构造参数

    Args:
        yaml_path: triplet yaml 文件路径（如 m22_encouraged.yaml）

    Returns:
        dict with keys:
          - baby_id: str
          - value_conflict_prob: float
          - distribution_by_epoch: Dict[int, Dict[str, float]]
          - description: str（可选）

    Raises:
        FileNotFoundError: yaml 文件不存在
        ValueError: yaml 缺少必需字段
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Triplet yaml not found: {yaml_path}")

    with open(yaml_path) as f:
        cfg = yaml.safe_load(f)

    # 验证必需字段
    required = ['baby_id', 'events']
    for key in required:
        if key not in cfg:
            raise ValueError(f"yaml missing required field: {key}")

    events = cfg['events']
    if 'value_conflict_prob' not in events:
        raise ValueError("yaml missing events.value_conflict_prob")
    if 'distribution_by_epoch' not in events:
        raise ValueError("yaml missing events.distribution_by_epoch")

    # 转换 distribution_by_epoch keys 为 int（yaml load 后是 int，但显式确保）
    distribution_by_epoch = {
        int(k): v for k, v in events['distribution_by_epoch'].items()
    }

    return {
        'baby_id': cfg['baby_id'],
        'description': cfg.get('description', ''),
        'value_conflict_prob': float(events['value_conflict_prob']),
        'distribution_by_epoch': distribution_by_epoch,
    }


# ── 便捷常量 ──────────────────────────────────────

# 3 个 triplet config 路径（相对于本文件所在目录的 ../configs/）
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
TRIPLET_CONFIGS = {
    'encouraged': str(_CONFIG_DIR / "m22_encouraged.yaml"),
    'challenged': str(_CONFIG_DIR / "m22_challenged.yaml"),
    'uncertain':  str(_CONFIG_DIR / "m22_uncertain.yaml"),
}


if __name__ == "__main__":
    # 自检：3 个 yaml 都能正确加载
    import sys
    sys.path.insert(0, '.')

    print("=" * 60)
    print("  Triplet config loader 自检")
    print("=" * 60)
    print()

    for name, path in TRIPLET_CONFIGS.items():
        try:
            cfg = load_triplet_config(path)
            print(f"✓ {name}:")
            print(f"  baby_id: {cfg['baby_id']}")
            print(f"  value_conflict_prob: {cfg['value_conflict_prob']}")
            dist = cfg['distribution_by_epoch']
            print(f"  distribution_by_epoch 阶段数: {len(dist)}")
            for epoch_start in sorted(dist.keys()):
                w = dist[epoch_start]
                print(f"    epoch {epoch_start}+: "
                      f"success={w['success']:.2f} failure={w['failure']:.2f}")
            print()
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            sys.exit(1)

    print("✓ 3 个 triplet config 全部加载成功")
