#!/bin/bash
# Caps 反向切换：英文(ABC) -> 中文(鼠须管)
# 本机 TISSelectInputSource API 损坏，用偏好写入 + 菜单代理重启的方式切换
defaults write com.apple.HIToolbox AppleSelectedInputSources -array \
  '{"Bundle ID"="im.rime.inputmethod.Squirrel"; "Input Mode"="im.rime.inputmethod.Squirrel.Hans"; InputSourceKind="Input Mode";}'
killall TextInputMenuAgent 2>/dev/null
