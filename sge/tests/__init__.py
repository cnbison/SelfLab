# sge/tests — Phase 3.2 单元测试
#
# 策略：
# - 复用 sge/*_unit_tests() 内的 assert 逻辑，提取为 pytest test_ 函数
# - 保留原 _run_*_unit_tests() 向后兼容（python -m sge.X 仍可跑）
# - conftest.py 提供共享 fixtures（tmp_db / stub_llm）
# - 覆盖率用 pytest-cov，目标 ≥ 80%