#!/bin/bash
# M2.2 E4 watchdog — 监控 PID 12569 状态 + log 活动 + epoch 进度
#
# 报警条件（任一触发即 ALERT）：
#   1. 进程死亡
#   2. log 文件 10 分钟无写入
#   3. epoch 进度 10 分钟无推进
#
# 状态报告频率：每 60 秒
# 报警时打印到 stdout + append 到 /tmp/e4_watchdog.log
#
# 用法：
#   chmod +x watchdog_e4.sh
#   ./watchdog_e4.sh
# 或后台：
#   nohup ./watchdog_e4.sh > /tmp/watchdog_stdout.log 2>&1 &

set -u

PID=${1:-12569}
LOG_FILE=${2:-/tmp/m22_triplets_v3.log}
STALE_THRESHOLD=${3:-600}  # 10 分钟（秒）
REPORT_INTERVAL=60

LAST_EPOCH=""
LAST_LOG_MTIME=""
STALE_COUNT=0

echo "=== E4 Watchdog Started ==="
echo "  PID: $PID"
echo "  Log: $LOG_FILE"
echo "  Stale threshold: ${STALE_THRESHOLD}s"
echo "  Report interval: ${REPORT_INTERVAL}s"
echo ""

while true; do
    NOW=$(date +%s)
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

    # ── 1. 进程状态 ──
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "[$TIMESTAMP] ❌ ALERT: PID $PID is DEAD"
        echo "[$TIMESTAMP] ❌ ALERT: PID $PID is DEAD" >> /tmp/e4_watchdog.log
        # 不退出 — 让用户决定是否需要重启（手动）
    fi

    # ── 2. 当前 epoch ──
    if [ -f "$LOG_FILE" ]; then
        CURRENT_EPOCH=$(grep -oE "\[epoch [0-9]+/1000\]" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oE "[0-9]+" || echo "0")
        LOG_MTIME=$(stat -f %m "$LOG_FILE" 2>/dev/null || echo "0")
    else
        CURRENT_EPOCH="0"
        LOG_MTIME="0"
    fi

    # ── 3. 计算 idle 时间 ──
    LOG_IDLE=$((NOW - LOG_MTIME))

    # ── 4. 状态报告（每 60s）──
    if [ "$CURRENT_EPOCH" != "$LAST_EPOCH" ] || [ "$LOG_MTIME" != "$LAST_LOG_MTIME" ]; then
        # 有进展
        echo "[$TIMESTAMP] ✓ Active: epoch=$CURRENT_EPOCH log_idle=${LOG_IDLE}s"
        STALE_COUNT=0
        LAST_EPOCH="$CURRENT_EPOCH"
        LAST_LOG_MTIME="$LOG_MTIME"
    else
        # 无进展
        STALE_COUNT=$((STALE_COUNT + REPORT_INTERVAL))
        echo "[$TIMESTAMP] ⏳ Idle ${STALE_COUNT}s: epoch=$CURRENT_EPOCH log_idle=${LOG_IDLE}s"

        if [ "$STALE_COUNT" -ge "$STALE_THRESHOLD" ]; then
            echo "[$TIMESTAMP] ❌ ALERT: No activity for ${STALE_COUNT}s (threshold=${STALE_THRESHOLD}s)"
            echo "[$TIMESTAMP] ❌ ALERT: No activity for ${STALE_COUNT}s" >> /tmp/e4_watchdog.log
            echo "[$TIMESTAMP]    PID=$PID EPOCH=$CURRENT_EPOCH LOG_IDLE=${LOG_IDLE}s"
            echo "[$TIMESTAMP]    最近 retry:"
            grep "\[LLM retry" "$LOG_FILE" 2>/dev/null | tail -3 | sed "s/^/    /"
            echo "[$TIMESTAMP]    最近进程状态:"
            ps -o pid,etime,pcpu,command -p $PID 2>/dev/null | tail -1 | sed "s/^/    /"
        fi
    fi

    sleep $REPORT_INTERVAL
done
