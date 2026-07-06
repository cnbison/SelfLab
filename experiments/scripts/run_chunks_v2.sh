#!/bin/bash
# M2.2 v2 chunk wrapper — 串行跑 N 个 chunk（默认 12 = 3 baby × 4 chunk）
#
# 与 run_chunks.sh (E4) 的区别：
#   - 用 m22_v2_exph_self.py 脚本（含 H_self + meaning 跟踪）
#   - 输出到 output/m22_v2_exph_self/（与 E4 m22_triplets/ 并列）
#   - 支持 --babies / --max-chunks-per-baby 灵活控制范围
#
# 每个 chunk：250 epochs，独立 SGELLMClient，~30 min
# chunk 间 sleep 5 分钟（让 server 恢复）
# 已完成的 chunk 自动 skip
#
# 总预计时间（默认 12 chunks）：
#   - 12 chunks × ~30 min = 6 hours
#   - 11 gaps × 5 min = 55 min
#   - 总 ~7 hours
#
# 用法：
#   chmod +x run_chunks_v2.sh
#   ./run_chunks_v2.sh                                       # 跑全部 12 chunks
#   ./run_chunks_v2.sh --max-chunks-per-baby 1               # 只跑每个 baby 的 chunk 0（~1.5h）
#   ./run_chunks_v2.sh --babies encouraged                    # 只跑 encouraged × 4 chunks
#   ./run_chunks_v2.sh --babies encouraged --max-chunks 1    # 只跑 encouraged chunk 0（~30 min 烟测）
#   ./run_chunks_v2.sh --dedup-threshold 0.3                  # 启用 IdentityLayer/Narrative 去重（M3.x 试点）

set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
V2_SCRIPT="$SCRIPT_DIR/m22_v2_exph_self.py"
BABIES=("encouraged" "challenged" "uncertain")
CHUNKS=(0 1 2 3)
GAP_SECONDS=${GAP_SECONDS:-300}  # chunk 间 sleep（默认 5 分钟）

LOG_FILE=${LOG_FILE:-/tmp/m22_v2_chunks_run.log}

# 解析自定义参数
CUSTOM_BABIES=()
CUSTOM_MAX_CHUNKS=0
DEDUP_THRESHOLD=0.0
DEDUP_WINDOW=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --babies)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                CUSTOM_BABIES+=("$1")
                shift
            done
            ;;
        --max-chunks-per-baby|--max-chunks)
            shift
            CUSTOM_MAX_CHUNKS="$1"
            shift
            ;;
        --dedup-threshold)
            shift
            DEDUP_THRESHOLD="$1"
            shift
            ;;
        --dedup-window)
            shift
            DEDUP_WINDOW="$1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ ${#CUSTOM_BABIES[@]} -gt 0 ]; then
    BABIES=("${CUSTOM_BABIES[@]}")
fi
if [ "$CUSTOM_MAX_CHUNKS" -gt 0 ]; then
    CHUNKS=($(seq 0 $((CUSTOM_MAX_CHUNKS - 1))))
fi

# 根据 dedup 选 output dir
if [ "$(echo "$DEDUP_THRESHOLD > 0" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    RESULT_DIR="/Users/loubicheng/project/SelfLab/experiments/output/m22_v3_dedup"
else
    RESULT_DIR="/Users/loubicheng/project/SelfLab/experiments/output/m22_v2_exph_self"
fi

TOTAL_CHUNKS=$((${#BABIES[@]} * ${#CHUNKS[@]}))

echo "=== M2.2 v2 Chunk Wrapper ==="
echo "  V2 script: $V2_SCRIPT"
echo "  Babies: ${BABIES[@]}"
echo "  Chunks per baby: ${CHUNKS[@]}"
echo "  Total: $TOTAL_CHUNKS chunks"
echo "  Gap between chunks: ${GAP_SECONDS}s"
echo "  Dedup threshold: $DEDUP_THRESHOLD (window=$DEDUP_WINDOW)"
echo "  Result dir: $RESULT_DIR"
echo "  Log: $LOG_FILE"
echo ""

> "$LOG_FILE"

TOTAL_T0=$(date +%s)
TOTAL_DONE=0
SUCCEEDED=0
FAILED=0
SKIPPED=0

for baby in "${BABIES[@]}"; do
    for chunk in "${CHUNKS[@]}"; do
        TOTAL_DONE=$((TOTAL_DONE + 1))
        CHUNK_T0=$(date +%s)

        echo "" | tee -a "$LOG_FILE"
        echo "===============================================" | tee -a "$LOG_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$TOTAL_DONE/$TOTAL_CHUNKS] " \
             "Starting $baby chunk $chunk" | tee -a "$LOG_FILE"
        echo "===============================================" | tee -a "$LOG_FILE"

        RESULT_FILE="$RESULT_DIR/${baby}_chunk${chunk}_result.json"
        if [ -f "$RESULT_FILE" ]; then
            echo "  ⊙ SKIP $baby chunk $chunk（已有 $RESULT_FILE）" | tee -a "$LOG_FILE"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi

        CHUNK_LOG="/tmp/m22_v2_chunk_${baby}_${chunk}.log"
        python "$V2_SCRIPT" \
            --baby "$baby" \
            --chunk-index "$chunk" \
            --dedup-threshold "$DEDUP_THRESHOLD" \
            --dedup-window "$DEDUP_WINDOW" \
            > "$CHUNK_LOG" 2>&1
        EXIT_CODE=$?

        CHUNK_ELAPSED=$(( $(date +%s) - CHUNK_T0 ))

        if [ $EXIT_CODE -eq 0 ]; then
            SUCCEEDED=$((SUCCEEDED + 1))
            echo "  ✓ $baby chunk $chunk 完成 (${CHUNK_ELAPSED}s)" | tee -a "$LOG_FILE"
        else
            FAILED=$((FAILED + 1))
            echo "  ✗ $baby chunk $chunk 失败 (exit=$EXIT_CODE, ${CHUNK_ELAPSED}s)" | tee -a "$LOG_FILE"
            echo "    详见: $CHUNK_LOG" | tee -a "$LOG_FILE"
        fi

        # Chunk 间 sleep（最后一个 chunk 不 sleep）
        if [ "$TOTAL_DONE" -lt "$TOTAL_CHUNKS" ]; then
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
echo "下一步: 运行 python $V2_SCRIPT --aggregate-only 合并结果"