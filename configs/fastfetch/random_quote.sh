#!/bin/bash

QUOTE_FILE="$HOME/.config/fastfetch/quotes.txt"
STATE_FILE="$HOME/.config/fastfetch/.quote_sequence"

# 读取所有非空短句
all_quotes=()
if [ -f "$QUOTE_FILE" ] && [ -s "$QUOTE_FILE" ]; then
    mapfile -t all_quotes < <(grep -v '^[[:space:]]*$' "$QUOTE_FILE")
fi

# 如果没有有效短句，输出默认并退出
if [ ${#all_quotes[@]} -eq 0 ]; then
    echo "Stay libre"
    exit 0
fi

# 读取剩余列表
remaining=()
if [ -f "$STATE_FILE" ] && [ -s "$STATE_FILE" ]; then
    mapfile -t remaining < "$STATE_FILE"
fi

# 如果剩余列表为空，重新打乱
if [ ${#remaining[@]} -eq 0 ]; then
    if command -v shuf &>/dev/null; then
        mapfile -t remaining < <(shuf -e "${all_quotes[@]}")
    else
        # 降级方案（sort -R 可能较慢，但可用）
        mapfile -t remaining < <(sort -R <<< "$(printf '%s\n' "${all_quotes[@]}")")
    fi
    # 若打乱后仍为空（极罕见），直接使用 all_quotes
    if [ ${#remaining[@]} -eq 0 ]; then
        remaining=("${all_quotes[@]}")
    fi
fi

# 取第一条
selected="${remaining[0]}"

# 更新剩余列表
new_remaining=("${remaining[@]:1}")

# 写入状态文件（若为空则清空）
if [ ${#new_remaining[@]} -eq 0 ]; then
    > "$STATE_FILE"
else
    printf "%s\n" "${new_remaining[@]}" > "$STATE_FILE"
fi

echo "$selected"