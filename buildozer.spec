[app]
title = 蒲江房产带看
package.name = pujiang_agent
package.domain = org.pujiang

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,json

version = 1.0
requirements = python3,kivy==2.3.1,requests,openssl,urllib3

orientation = portrait
fullscreen = 0

# apk 要连云服务器，需要网络权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# 只编 arm64，鸿蒙手机就是 arm64，缩短编译时间
android.arch = arm64-v8a

android.api = 35
android.minapi = 21

android.skip_update = False
android.accept_sdk_license = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 0
