#!/bin/bash
# M2.2 E4 chunk wrapper — 串行跑 12 个 chunk（3 baby × 4 chunk）
#
# 每个 chunk：250 epochs，独立 SGELLMClient，~30 min
# chunk 间 sleep 5 分钟（让 MiniMax server 恢复）
# 已完成的 chunk 自动 skip（检测 {name}_chunk{N}_result.json）
# 监控：每个 chunk 启动 watchdog_e4.sh
#
# 总预计时间：
# - 12 chunks × ~30 min = 6 hours
# - 11 gaps × 5 min = 55 min
# - 总 ~7 hours
#
# 用法：
#   chmod +x run_chunks.sh
#   ./run_chunks.sh              # 跑全部 12 chunks
#   ./run_chunks.sh 2>&1 | tee /tmp/chunks_run.log   # 带 log

set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
E4_SCRIPT="$SCRIPT_DIR/m22_triplets.py"
WATCHDOG="$SCRIPT_DIR/watchdog_e4.sh"
BABIES=("encouraged" "challenged" "uncertain")
CHUNKS=(0 1 2 3)
GAP_SECONDS=${GAP_SECONDS:-300}  # chunk 间 sleep（默认 5 分钟）

LOG_FILE=${LOG_FILE:-/tmp/m22_chunks_run.log}
SUMMARY_FILE="/tmp/m22_chunks_summary.log"

echo "=== M2.2 E4 Chunk Wrapper ==="
echo "  E4 script: $E4_SCRIPT"
echo "  Babies: ${BABIES[@]}"
echo "  Chunks per baby: ${CHUNKS[@]}"
echo "  Gap between chunks: ${GAP_SECONDS}s"
echo "  Total: 12 chunks"
echo "  Log: $LOG_FILE"
echo ""

# 清理旧 log
> "$LOG_FILE"
> "$SUMMARY_FILE"

TOTAL_T0=$(date +%s)
TOTAL_CHUNKS=0
SUCCEEDED=0
FAILED=0
SKIPPED=0

for baby in "${BABIES[@]}"; do
    for chunk in "${CHUNKS[@]}"; do
        TOTAL_CHUNKS=$((TOTAL_CHUNKS + 1))
        CHUNK_T0=$(date +%s)

        echo "" | tee -a "$LOG_FILE"
        echo "===============================================" | tee -a "$LOG_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$TOTAL_CHUNKS/12] " \
             "Starting $baby chunk $chunk" | tee -a "$LOG_FILE"
        echo "===============================================" | tee -a "$LOG_FILE"

        # Skip 检测
        RESULT_FILE="/Users/loubicheng/project/SelfLab/experiments/output/m22_triplets/${baby}_chunk${chunk}_result.json"
        if [ -f "$RESULT_FILE" ]; then
            echo "  ⊙ SKIP $baby chunk $chunk（已有 $RESULT_FILE）" | tee -a "$LOG_FILE"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi

        # 启动 E4 单 chunk
        # 每个 chunk 用独立 log 文件便于排查
        CHUNK_LOG="/tmp/m22_chunk_${baby}_${chunk}.log"
        python "$E4_SCRIPT" \
            --baby "$baby" \
            --chunk-index "$chunk" \
            > "$CHUNK_LOG" 2>&1
        EXIT_CODE=$?

        CHUNK_ELAPSED=$(( $(date +%s) - CHUNK_T0 ))

        if [ $EXIT_CODE -eq 0 ]; then
            SUCCEEDED=$((SUCCEEDED + 1))
            echo "  ✓ $baby chunk $chunk 完成 (${CHUNK_ELAPSED}s)" | tee -a "$LOG_FILE"
        else
            FAILED=$((FAILED + 1))
            echo "  ✗ $baby chunk $chunk 失败 (exit=$EXIT_CODE, ${CHUNK_ELAPSED}s)" | tee -a "$LOG_FILE"
            echo "    详见: $CHUNK_LOG"
            # 不 break — 让 wrapper 继续下一个 chunk
            # （用户可手动 Ctrl-C 中断）
        fi

        # Chunk 间 sleep（最后一个 chunk 不 sleep）
        if [ "$TOTAL_CHUNKS" -lt 12 ]; then
            echo "  ⏳ Sleep ${GAP_SECONDS}s 让 server 恢复..." | tee -a "$LOG_FILE"
            sleep "$GAP_SECONDS"
        fi
    done
done

TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_T0 ))

echo "" | tee -a "$LOG_FILE"
echo "===============================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 所有 chunks 完成" | tee -a "$LOG_FILE"
echo "===============================================" | tee -a "$LOG_FILE"
echo "  Total: $TOTAL_CHUNKS chunks" | tee -a "$LOG_FILE"
echo "  Succeeded: $SUCCEEDED" | tee -a "$LOG_FILE"
echo "  Failed: $FAILED" | tee -a "$LOG_FILE"
echo "  Skipped: $SKIPPED" | tee -a "$LOG_FILE"
echo "  Total elapsed: ${TOTAL_ELAPSED}s ($((TOTAL_ELAPSED/3600))h)" | tee -a "$LOG_FILE"

echo ""
echo "下一步: 运行 aggregate_chunks.py 合并结果"
