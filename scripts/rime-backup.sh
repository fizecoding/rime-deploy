#!/bin/bash
# Rime 输入法体系 iCloud 备份（词库 + userdb + 全部配置 + 脚本 + 启动项）
RIME="$HOME/Library/Rime/"
SCRIPTS="$HOME/Library/Scripts/"
LAUNCHAGENT="$HOME/Library/LaunchAgents/com.user.rime-backup.plist"
DEST="$HOME/Library/Mobile Documents/com~apple~CloudDocs/RimeBackup"

mkdir -p "$DEST"

# 词库与输入法配置（核心）
rsync -a --exclude 'build/' --exclude '.git/' --exclude 'trash/' "$RIME" "$DEST/Rime/"

# 自用脚本与备份任务自身
mkdir -p "$DEST/Scripts"
rsync -a "$SCRIPTS" "$DEST/Scripts/"
[ -f "$LAUNCHAGENT" ] && cp "$LAUNCHAGENT" "$DEST/"

date "+%Y-%m-%d %H:%M:%S" > "$DEST/.last_backup"
