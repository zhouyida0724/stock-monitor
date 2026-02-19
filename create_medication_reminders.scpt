-- 检查 Calendar 权限并创建吃药提醒日程
-- 三个时间: 12:00, 16:00, 20:00

tell application "Calendar"
    activate
    
    -- 获取默认日历
    set calList to calendars
    if (count of calList) = 0 then
        display dialog "没有找到可用的日历，请先创建一个日历。" buttons {"OK"} default button "OK"
        return
    end if
    
    set defaultCal to item 1 of calList
    set calName to name of defaultCal
    
    -- 吃药提醒时间列表 (小时)
    set medTimes to {12, 16, 20}
    set medLabels to {"中午的药", "下午的药", "晚上的药"}
    
    -- 获取今天的日期并设置为基准日期
    set baseDate to current date
    set time of baseDate to 0
    
    repeat with i from 1 to count of medTimes
        set medHour to item i of medTimes
        set medLabel to item i of medLabels
        
        -- 创建事件时间
        set eventStart to baseDate
        set eventStart's hours to medHour
        set eventStart's minutes to 0
        set eventStart's seconds to 0
        
        -- 如果是今天且时间已过，则从明天开始
        if eventStart < (current date) then
            set eventStart to eventStart + (1 * days)
        end if
        
        set eventEnd to eventStart + (30 * minutes) -- 30分钟事件
        
        -- 检查是否已存在相同的事件
        set eventExists to false
        set existingEvents to (every event of defaultCal whose start date = eventStart and summary = "吃药提醒 💊")
        if (count of existingEvents) > 0 then
            set eventExists to true
        end if
        
        if not eventExists then
            -- 创建事件
            tell defaultCal
                set newEvent to make new event with properties {summary:"吃药提醒 💊", start date:eventStart, end date:eventEnd, description:"提醒吃药 - " & medLabel}
                
                -- 添加每天重复的规则
                tell newEvent
                    -- 使用 recurrence 属性设置每天重复
                    set recurrence to "FREQ=DAILY"
                end tell
            end tell
            
            log "✅ 已创建: " & medLabel & " (" & medHour & ":00)"
        else
            log "⚠️ 已存在: " & medLabel & " (" & medHour & ":00)"
        end if
    end repeat
    
    display notification "吃药提醒已同步到日历" with title "✅ 完成"
    
end tell