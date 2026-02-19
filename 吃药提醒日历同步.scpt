(*
吃药提醒日历同步脚本
========================
此脚本将创建 3 个重复的吃药提醒日程：
- 12:00 中午的药
- 16:00 下午的药  
- 20:00 晚上的药

运行方式：
1. 双击此文件，或在 Script Editor 中打开并点击运行
2. 首次运行时会弹出权限请求，请点击"允许"
*)

-- 吃药时间配置
set medTimes to {{12, 0, "中午的药"}, {16, 0, "下午的药"}, {20, 0, "晚上的药"}}

tell application "Calendar"
    activate
    
    -- 尝试找到合适的日历
    try
        -- 优先找包含"提醒"或"Reminders"的日历
        set targetCal to first calendar whose name contains "提醒" or name contains "Reminder"
    on error
        try
            -- 否则找第一个可写的日历
            set targetCal to first calendar whose writable is true
        on error
            -- 如果没有合适的，创建新日历
            set targetCal to make new calendar with properties {name:"吃药提醒"}
        end try
    end try
    
    set calName to name of targetCal
    
    set createdCount to 0
    set existingCount to 0
    
    repeat with medInfo in medTimes
        set medHour to item 1 of medInfo
        set medMin to item 2 of medInfo
        set medLabel to item 3 of medInfo
        
        -- 设置事件开始时间
        set startTime to (current date)
        set hours of startTime to medHour
        set minutes of startTime to medMin
        set seconds of startTime to 0
        
        -- 如果今天已过，设为明天
        if startTime < (current date) then
            set startTime to startTime + (1 * days)
        end if
        
        set endTime to startTime + (30 * minutes)
        
        -- 检查事件是否已存在
        set existingEvents to (every event of targetCal whose start date ≥ startTime and start date ≤ (startTime + 1) and summary = "吃药提醒 💊")
        
        if (count of existingEvents) = 0 then
            tell targetCal
                set newEvent to make new event with properties {¬
                    summary:"吃药提醒 💊", ¬
                    description:"提醒吃药 - " & medLabel, ¬
                    start date:startTime, ¬
                    end date:endTime}
                set recurrence of newEvent to "FREQ=DAILY"
            end tell
            set createdCount to createdCount + 1
            log "✅ 已创建: " & medLabel & " (" & medHour & ":00)"
        else
            set existingCount to existingCount + 1
            log "⚠️ 已存在: " & medLabel & " (" & medHour & ":00)"
        end if
    end repeat
    
    -- 显示结果
    set resultMsg to "已完成！

"
    if createdCount > 0 then
        set resultMsg to resultMsg & "✅ 新建 " & createdCount & " 个提醒
"
    end if
    if existingCount > 0 then
        set resultMsg to resultMsg & "⚠️ 已有 " & existingCount & " 个提醒
"
    end if
    set resultMsg to resultMsg & "
📅 日历: " & calName & "
🔄 重复: 每天"
    
    display notification resultMsg with title "吃药提醒设置完成"
    return resultMsg
end tell