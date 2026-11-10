# rime-deploy — 全本地个人输入法体系

基于 [白霜拼音 rime-frost](https://github.com/gaboolic/rime-frost) 的个人配置与工具集：自有 Rime 配置、微信语料训练个人词库、iCloud 定时备份。从实机部署脱敏整理而来，完整过程见 [docs/部署全记录.md](docs/部署全记录.md)。

## 架构

| 组件 | 位置 | 作用 |
|---|---|---|
| 鼠须管 Squirrel | /Library/Input Methods/ | Rime 前端 |
| 白霜词库 rime-frost | ~/Library/Rime/（git 仓库） | 185 万词基础词库 + 全部方案（上游） |
| 个人中文词频 | personal.dict.yaml | 语料训练产物（本库存脱敏样例） |
| 个人英文词库 | en_dicts/personal_en.dict.yaml | 同上 |
| 动态学习层 | rime_frost.userdb | 日常打字实时调频（自动） |
| 备份 | iCloud 云盘/RimeBackup | 每天 22:00 + 开机增量 |

词库三层：静态底座（白霜 cn_dicts）→ 个人词频（训练产物）→ 动态学习（userdb）。
聚合点：`rime_frost.dict.yaml` import_tables 挂 `- personal`；`melt_eng.dict.yaml` 挂 `- en_dicts/personal_en`（install.sh 自动处理，白霜 `git pull` 覆盖后重跑即可）。

## 目录

```
rime/      自有 Rime 配置（*.custom.yaml、easy_en 方案、custom_phrase 追加段、词库样例）
corpus/    语料提取与训练脚本（extract_my_messages.py / train_personal_dict.py）
scripts/   rime-backup.sh、caps-switch-cn.sh、set_caps_led.c、备份 LaunchAgent
docs/      部署全记录 / 配置说明 / 恢复指南
```

## 全新部署

```bash
brew install --cask squirrel
git clone https://github.com/gaboolic/rime-frost ~/Library/Rime
git clone <本仓库> && cd rime-deploy
./install.sh
# 系统设置 → 键盘 → 输入法：添加 鼠须管（简体）+ ABC
# 鼠须管菜单 → 重新部署
```

easy_en 英文联想方案还需要上游词表 `easy_en.dict.yaml`（easy-en 项目，约 3MB，不入本库），放入 `~/Library/Rime/`。

## 语料训练

```bash
# 1. 微信解密库 → 本人纯文本消息（解密工具见 wcdb-key-tool，过程见部署全记录阶段 3）
python3 corpus/extract_my_messages.py <decrypted/message> <本人wxid> my_messages.txt

# 2. 语料 → 个人词频词典（需 jieba、pypinyin）
pip3 install jieba pypinyin
python3 corpus/train_personal_dict.py my_messages.txt ~/Library/Rime ~/Library/Rime/personal.dict.yaml
# 鼠须管菜单 → 重新部署
```

训练后删除明文数据：`rm -rf ~/wxexport/decrypted ~/wxexport/db_storage ~/wxexport/all_keys.json`

## 常用命令

```bash
# 重新部署
"/Library/Input Methods/Squirrel.app/Contents/MacOS/rime_deployer" --build \
  ~/Library/Rime "/Library/Input Methods/Squirrel.app/Contents/SharedSupport" ~/Library/Rime/build
killall Squirrel; sleep 1; open "/Library/Input Methods/Squirrel.app"

# 手动备份
bash ~/Library/Scripts/rime-backup.sh

# 更新白霜（会覆盖 import_tables，需重跑 ./install.sh）
cd ~/Library/Rime && git pull
```

灾备恢复场景见 [docs/恢复指南.md](docs/恢复指南.md)。

## 已知限制

1. 本机 `TISSelectInputSource` API 损坏：程序化切换输入源 paramErr，重启无效；切换一律走 Rime 内部（F4 / Ctrl+`），应急用 `caps-switch-cn.sh`（偏好写入 + 重启 TextInputMenuAgent）。
2. 这版 Squirrel 的 librime-lua 不加载 lua/ 模块：白霜 Lua 功能静默失效，**不要往方案里加 lua 组件**。
3. `Cmd+任意键` 不进输入法（macOS 规定）：清码用 Esc / Ctrl+Backspace。
4. `recognizer` 先于 `key_binder`：`ascii_raw` 字符集必须排除 `-` 和 `=`，否则候选翻页失效。
5. macOS 27 禁止用户态写键盘灯：`set_caps_led.c` 写灯被拒，仅作 HID 诊断工具。

## 脱敏说明

入库内容均不含个人标识：词库只保留格式样例（完整词库由训练脚本再生）；聊天语料、解密密钥与数据库、easy_en 大词表、白霜本体（上游 git）均不在库内；LaunchAgent 中用户路径以 `__HOME__` 占位，install.sh 自动替换。
