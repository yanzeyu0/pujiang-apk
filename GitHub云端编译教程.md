# 安卓 apk 云端编译教程

安卓原生 apk 用 GitHub Actions 云端编译（本机 Windows 编不了 Kivy APK，之前已验证）。V0 中文修复版就是这么编出来的，流程已跑通。

## 一、准备 GitHub Token（只需一次）

1. 登录 GitHub（账号 `yanzeyu0`）
2. 头像 → Settings → Developer settings → Personal access tokens → Tokens (classic)
3. Generate new token (classic)，勾选权限：**repo**、**workflow**
4. 生成后复制那串 token（只显示一次）

## 二、上传代码

1. 用记事本打开本目录的 `上传到GitHub.bat`
2. 把 `set GH_TOKEN=PASTE_YOUR_TOKEN_HERE` 里的 `PASTE_YOUR_TOKEN_HERE` 换成你刚复制的 token，保存
3. 双击 `上传到GitHub.bat`，它会自动把整个 apk 工程推到 GitHub 仓库 `pujiang-apk`

> 如果提示仓库不存在：去 GitHub 新建一个空仓库叫 `pujiang-apk`（不要勾 README），再重跑脚本。

## 三、触发编译

1. 打开 `https://github.com/yanzeyu0/pujiang-apk/actions`
2. 左边点 **Build PuJiang APK** → 右边 **Run workflow** → 绿色按钮确认
3. 等 10～20 分钟（首次编译慢，后续有缓存会快很多）

## 四、下载 apk

1. 编译完成后，点进这次运行记录，页面底部 **Artifacts** 里有 `pujiang-apk`
2. 下载解压得到 `.apk`（在 `bin/` 里）
3. 传到手机，用卓易通安装（和 V0 中文修复版一样的装法）

## 五、用之前要做两件事

1. **更新服务器后端**（房源编辑接口）：按 `backend/更新服务器说明.md` 操作，否则编辑房源会报错
2. **服务器地址**：apk 默认连 `http://159.75.108.130`。如需改，进应用点右上角「设置」填新地址

## 常见问题

| 现象 | 处理 |
|---|---|
| Build APK 步骤失败 | 点进运行日志看红色报错，发给我 |
| apk 装不上 | 确认是 arm64 架构；卓易通要支持安卓 13+ |
| 打开显示中文方块 | 确认 `chinese_font.ttf` 一起上传了（9.7MB）|
| 连不上服务器 | 应用内「设置」检查地址；服务器 80 端口是否放行 |
