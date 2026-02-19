-- 创建吃药提醒日程 - 简化版

set medTimes to {{12, 0, "中午的药"}, {16, 0, "下午的药"}, {20, 0, "晚上的药"}}

tell application "Calendar"
    -- 获取或创建"提醒"日历
    try
        set targetCal to first calendar whose name contains "提醒" or name contains "Reminder"
    on error
        try
            set targetCal to first calendar whose writable is true
        on error
            set targetCal to make new calendar with properties {name:"吃药提醒"}
        end try
    end try
    
    set calName to name of targetCal
    
    repeat with medInfo in medTimes
        set medHour to item 1 of medInfo
        set medMin to item 2 of medInfo
        set medLabel to item 3 of medInfo
        
        -- 设置时间
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
                set newEvent to make new event with properties {summary:"吃药提醒 💊", description:"提醒吃药 - " & medLabel, start date:startTime, end date:endTime}
                set recurrence of newEvent to "FREQ=DAILY"
            end tell
            log "✅ 已创建 " & medLabel & " (" & medHour & ":00)"
        else
            log "⚠️ 已存在 " & medLabel & " (" & medHour & ":00)"
        end if
    end repeat
    
    return "完成！已将吃药提醒添加到日历: " & calName
end tell