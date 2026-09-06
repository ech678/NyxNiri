#!/bin/bash

LOGO_DIR="$HOME/.config/fastfetch/logos"
STATE_FILE="$HOME/.config/fastfetch/.logo_sequence"
FIRST_FILE="$HOME/.config/fastfetch/.logo_first"

# 获取所有图片（按文件名排序，保证一致性）
all_pics=()
while IFS= read -r -d '' file; do
    all_pics+=("$file")
done < <(find "$LOGO_DIR" -maxdepth 1 -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.webp" \) -print0 2>/dev/null | sort -z)

if [ ${#all_pics[@]} -eq 0 ]; then
    exit 1   # 无图片，fastfetch 使用默认
fi

# 读取剩余列表
remaining_pics=()
if [ -f "$STATE_FILE" ] && [ -s "$STATE_FILE" ]; then
    mapfile -t remaining_pics < "$STATE_FILE"
fi

# 如果剩余列表为空（首次运行或轮完一轮），重新打乱并检查首图重复
if [ ${#remaining_pics[@]} -eq 0 ]; then
    # 读取上一轮第一张
    first=""
    if [ -f "$FIRST_FILE" ]; then
        read -r first < "$FIRST_FILE"
    fi

    # 打乱函数（使用 shuf 或 sort -R）
    shuffle() {
        if command -v shuf &>/dev/null; then
            shuf -e "$@"
        else
            sort -R <<< "$(printf '%s\n' "$@")"
        fi
    }

    # 尝试最多 5 次生成新的打乱列表
    attempts=0
    max_attempts=5
    while true; do
        mapfile -t candidate < <(shuffle "${all_pics[@]}")
        # 如果候选列表为空，直接使用 all_pics（后备）
        if [ ${#candidate[@]} -eq 0 ]; then
            candidate=("${all_pics[@]}")
        fi
        # 检查首图是否与上一轮相同（如果 first 不为空）
        if [ -n "$first" ] && [ "${candidate[0]}" = "$first" ]; then
            # 若相同，交换第一张与第二张（如果列表长度 > 1）
            if [ ${#candidate[@]} -gt 1 ]; then
                temp="${candidate[0]}"
                candidate[0]="${candidate[1]}"
                candidate[1]="$temp"
                # 交换后若仍相同（可能只有两张且相同？不可能，因为文件路径不同），但为保险再检查
                if [ "${candidate[0]}" = "$first" ] && [ ${#candidate[@]} -gt 2 ]; then
                    # 再与第三张交换
                    temp="${candidate[0]}"
                    candidate[0]="${candidate[2]}"
                    candidate[2]="$temp"
                fi
            fi
            # 如果经过交换后仍相同（比如只有一张图），则保留原样（无法避免）
            if [ "${candidate[0]}" = "$first" ] && [ ${#candidate[@]} -eq 1 ]; then
                # 只有一张图，无法避免，直接使用
                :
            else
                # 新首图已不同，跳出
                break
            fi
        else
            # 首图不同，跳出
            break
        fi
        attempts=$((attempts + 1))
        if [ $attempts -ge $max_attempts ]; then
            # 超过尝试次数，强制用当前 candidate（即使重复）
            break
        fi
    done
    remaining_pics=("${candidate[@]}")
fi

# 取第一张
selected="${remaining_pics[0]}"

# 更新剩余列表（去掉第一张）
new_remaining=("${remaining_pics[@]:1}")

# 保存新的剩余列表（若为空则清空）
if [ ${#new_remaining[@]} -eq 0 ]; then
    > "$STATE_FILE"
else
    printf "%s\n" "${new_remaining[@]}" > "$STATE_FILE"
fi

# 记录本轮第一张（用于下一轮检查）
echo "$selected" > "$FIRST_FILE"

# 输出路径
echo "$selected"