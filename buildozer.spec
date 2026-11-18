[app]
title = 蒲江房产带看
package.name = pujiang_agent
package.domain = org.pujiang

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,json,ico

# App 图标（房+钥匙，科技蓝）
icon = icon.png

version = 1.1
requirements = python3,kivy==2.3.1,requests,openssl,urllib3,pillow

orientation = portrait
fullscreen = 0

# 网络 + 读取相册图片权限（Android 13+ 用 READ_MEDIA_IMAGES）
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

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
