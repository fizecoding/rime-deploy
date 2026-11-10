#!/bin/bash
# 覆盖安装：rime/ → ~/Library/Rime，scripts/ → ~/Library/Scripts，并装好备份 LaunchAgent
# 前提：鼠须管已安装，白霜已 clone 到 ~/Library/Rime
set -euo pipefail
cd "$(dirname "$0")"

RIME="$HOME/Library/Rime"
SCRIPTS="$HOME/Library/Scripts"
LA="$HOME/Library/LaunchAgents/com.user.rime-backup.plist"

if [ ! -d "$RIME/.git" ]; then
  echo "未找到白霜仓库，先执行:"
  echo "  git clone https://github.com/gaboolic/rime-frost \"$RIME\""
  exit 1
fi

# 1. 自有配置
cp rime/*.custom.yaml rime/easy_en.schema.yaml "$RIME/"

# 2. 词库样例（不覆盖已有训练产物）
[ -f "$RIME/personal.dict.yaml" ] || cp rime/personal.dict.yaml "$RIME/"
mkdir -p "$RIME/en_dicts"
[ -f "$RIME/en_dicts/personal_en.dict.yaml" ] || cp rime/en_dicts/personal_en.dict.yaml "$RIME/en_dicts/"

# 3. 自定义短语追加到白霜 custom_phrase.txt（幂等）
if ! grep -q "rime-deploy custom phrases" "$RIME/custom_phrase.txt" 2>/dev/null; then
  printf "\n# rime-deploy custom phrases\n" >> "$RIME/custom_phrase.txt"
  grep -v "^#" rime/custom_phrase.txt | grep -v "^$" >> "$RIME/custom_phrase.txt" || true
fi

# 4. 词库聚合点：rime_frost 挂 personal，melt_eng 挂 personal_en（白霜 git pull 后会被覆盖，重跑本脚本即可）
grep -q "^  - personal$" "$RIME/rime_frost.dict.yaml" || \
  sed -i '' 's|^  - cn_dicts/corrections.*|&\n  - personal         # 个人词频（语料训练）|' "$RIME/rime_frost.dict.yaml"
grep -q "^  - en_dicts/personal_en$" "$RIME/melt_eng.dict.yaml" || \
  sed -i '' 's|^  - en_dicts/en .*$|&\n  - en_dicts/personal_en # 个人英文词库|' "$RIME/melt_eng.dict.yaml"

# 5. easy_en 英文词表（上游，不入本库）：从 easy-en 项目取 easy_en.dict.yaml 放入 ~/Library/Rime/
[ -f "$RIME/easy_en.dict.yaml" ] || echo "[提示] 缺少 easy_en.dict.yaml（easy-en 上游词表），easy_en 方案暂不可用"

# 6. 脚本与定时备份
mkdir -p "$SCRIPTS" "$HOME/Library/LaunchAgents"
cp scripts/rime-backup.sh scripts/caps-switch-cn.sh scripts/set_caps_led.c "$SCRIPTS/"
sed "s|__HOME__|$HOME|g" scripts/com.user.rime-backup.plist > "$LA"
launchctl bootstrap "gui/$(id -u)" "$LA" 2>/dev/null || launchctl kickstart -k "gui/$(id -u)/com.user.rime-backup"

echo "完成。最后一步：鼠须管菜单 → 重新部署"
