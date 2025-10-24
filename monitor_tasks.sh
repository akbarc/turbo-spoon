#!/bin/bash

# Task Monitoring Script
# Checks status every 60 seconds and updates log

LOG_FILE="TASK_MONITORING_LOG.md"
COMPLETION_ORDER=()

# Task PIDs
declare -A TASKS=(
    [15]=38645
    [16]=39165
    [17]=39744
    [18]=40160
    [19]=40619
    [20]=41739
    [21]=42146
    [22]=42914
)

while true; do
    TIMESTAMP=$(date "+%I:%M:%S %p")
    echo ""
    echo "=== Status Check: $TIMESTAMP ==="

    # Check each task
    for task_num in 15 16 17 18 19 20 21 22; do
        pid=${TASKS[$task_num]}

        # Check if process is still running
        if ps -p $pid > /dev/null 2>&1; then
            # Get CPU and memory usage
            cpu_mem=$(ps -p $pid -o %cpu,%mem | tail -1)
            echo "Task $task_num (PID $pid): 🟡 RUNNING - $cpu_mem"
        else
            if [[ ! " ${COMPLETION_ORDER[@]} " =~ " Task $task_num " ]]; then
                COMPLETION_ORDER+=("Task $task_num")
                echo "Task $task_num (PID $pid): ✅ COMPLETED at $TIMESTAMP"

                # Append to log
                echo "" >> $LOG_FILE
                echo "### $TIMESTAMP - Task $task_num COMPLETED" >> $LOG_FILE
                echo "**Completion Position:** #${#COMPLETION_ORDER[@]}" >> $LOG_FILE
            else
                echo "Task $task_num (PID $pid): ✅ COMPLETED"
            fi
        fi
    done

    echo ""
    echo "Completion Order: ${COMPLETION_ORDER[*]}"
    echo "Completed: ${#COMPLETION_ORDER[@]}/8"

    # Exit if all tasks complete
    if [ ${#COMPLETION_ORDER[@]} -eq 8 ]; then
        echo ""
        echo "🎉 ALL TASKS COMPLETED!"
        echo ""
        echo "Final Completion Order:" >> $LOG_FILE
        for i in "${!COMPLETION_ORDER[@]}"; do
            echo "$((i+1)). ${COMPLETION_ORDER[$i]}" >> $LOG_FILE
        done
        echo "" >> $LOG_FILE
        echo "---" >> $LOG_FILE
        echo "*All tasks completed at $TIMESTAMP*" >> $LOG_FILE
        exit 0
    fi

    # Wait 60 seconds
    sleep 60
done
