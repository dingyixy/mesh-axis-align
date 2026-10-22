# GitHub 发布流程（维护者用）

本发布草稿根据 v1.3.0 安装包整理，尚未上传 GitHub。文档查询日期：2026-10-22。

## 一、准备仓库信息

推荐仓库名：`mesh-axis-align`。

推荐英文仓库 Description：

> Blender add-on for batch local-axis alignment and overlapping mesh deduplication, including post-import Ninja Ripper workflows.

中文简介：

> 面向 Ninja Ripper 等模型导入后处理流程的 Blender 插件，支持批量局部轴整理与所选重合网格去重。

可选 Topics：`blender`、`blender-addon`、`mesh-processing`、`ninja-ripper`、`deduplication`、`python`。

首页用 `README.md`（英文），顶部链接 `README.zh-CN.md`（中文）。两份介绍已写好，保留实际能力与限制，无需声称“还原游戏原始模型”。

## 二、发布前补齐两项信息

### 署名

当前插件 `bl_info` 的 `author` 仍为 `Codex`。选择你希望公开显示的维护者名称，例如 GitHub 用户名；如修改这里，随后按本文重新打包，使仓库源码与安装包一致。不要误填 Ninja Ripper 或 Blender 官方作为作者。

### 许可证

当前草稿和原安装包未附 LICENSE，不能把“仓库公开”直接当成已选择开源授权。请在公开发布前确定许可证并附完整文本。[GitHub 许可证说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

建议考虑 **GPL-3.0-or-later**。这是面向本 Blender 插件的发布建议，尚未替你实际设置授权。Blender 官方说明使用其 Python API 的公开插件应采用 GPL 兼容许可证。[Blender 官方许可说明](https://www.blender.org/about/license/)

若选择此方案：在 GitHub 创建或编辑根目录 `LICENSE`，使用 GNU GPL v3 完整模板；源码顶部添加 `# SPDX-License-Identifier: GPL-3.0-or-later`，并明确允许 v3 或后续版本。两份 README 分别追加“本项目采用 GNU GPL v3.0 或后续版本，见 LICENSE”及“This project is licensed under GNU GPL v3.0 or later. See LICENSE.”。安装 ZIP 中也包含 LICENSE。

## 三、整理发布目录

```text
mesh-axis-align/
├── README.md
├── README.zh-CN.md
├── LICENSE                  # 选择许可后补齐
├── .gitignore
├── mesh_axis_align.py
├── tests/
│   ├── test_mesh_axis_align.py
│   ├── test_mesh_axis_align_v12.py
│   └── test_mesh_axis_align_v13.py
├── docs/
│   ├── RELEASE-v1.3.0.md
│   └── PUBLISH.zh-CN.md
└── dist/
    └── mesh_axis_align_v1.3.0.zip
```

`dist/` 已在 `.gitignore` 中排除：源码进入仓库，ZIP 作为 Release 附件。浏览器上传不会替你遵守本地 `.gitignore`，应手动排除 dist。测试脚本已适配上述目录结构，基础测试中的旧报告文字断言也已更新。

仅上传这个独立发布目录中的文件，不要上传本次对话的整个工作目录。`work/` 运行环境、MCP 配置及备份、其他场景素材都不属于这个插件。

建议自行补充三张演示图：插件面板、倾斜长方体定轴前后、两个重合对象去重前后。用自建基础网格即可。存到 `docs/images/` 后在 README 引用；没有图片时当前 README 也可正常阅读。

## 四、重新打包并试安装

草稿 `dist/` 内暂时保留原 v1.3.0 ZIP，便于核对。修改作者或许可证后，需要重新打包；不要仅改仓库里的源码而继续上传旧包。

在**发布目录根目录**打开 PowerShell，补好 LICENSE 后执行：

```powershell
Compress-Archive -LiteralPath .\mesh_axis_align.py, .\LICENSE -DestinationPath .\dist\mesh_axis_align_v1.3.0.zip -Force
Get-FileHash -Algorithm SHA256 .\dist\mesh_axis_align_v1.3.0.zip
```

ZIP 内应直接有 `mesh_axis_align.py` 和 `LICENSE`，不要把整个仓库文件夹再次套进去。SHA256 可附在 Release 说明中，方便下载校验。

在临时 Blender 场景中安装 ZIP。传统插件通过“偏好设置 → 插件 → 从磁盘安装”，安装后还需启用。[Blender 4.5 插件安装说明](https://docs.blender.org/manual/fi/4.5/editors/preferences/addons.html)

检查：

1. 偏好设置版本显示 1.3.0，N 面板有三个按钮。
2. 创建倾斜、非等比缩放的长方体，复制一份并保持重合。
3. 「仅修改轴向」改变局部轴，两个对象仍保留且外形位置不变；Ctrl+Z 可撤销。
4. 「仅去重」只剩保留对象，其变换不变；Ctrl+Z 恢复两个对象。
5. 「全部执行」完成两项，可一次撤销。
6. 给重合对象设置不同 UV 或材质，验证严格匹配开启和关闭的区别。
7. 在独立后台 Blender 中运行 README 所列三份测试；使用完整 Blender 路径时，PowerShell 要写成 `& '你的路径/blender.exe' ...`。

此前版本实测环境是 Windows / Blender 4.5.3 LTS。不要在未测试前把 4.2、5.x、macOS 或 Linux 写成“已验证兼容”。

## 五、通过网页建立仓库

1. 登录 GitHub，右上角 **+ → New repository**。
2. Owner 选自己的账号，Repository name 填 `mesh-axis-align`，粘贴英文 Description。
3. 准备公开时选 **Public**；如果许可证、署名或截图还没整理好，也可先建立 Private 草稿仓库。
4. README 和 .gitignore 已有本地文件，可不勾选自动生成；许可证按上文选择，也可创建仓库后再新增。
5. 点击 **Create repository**。
6. 进入 **Add file → Upload files**，上传 README、源码、tests、docs 和 .gitignore，保留目录结构。不要上传 `dist`。
7. 提交说明可写 `Prepare Mesh Axis Align v1.3.0 release`，提交到 `main`。
8. 检查首页英文说明、中文链接、源码版本和 LICENSE 是否正确；在 About 设置中填写 Topics。

仓库创建的当前入口与可选项可参照 [GitHub 官方流程](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)。

## 六、发布可安装版本

1. 仓库首页进入 **Releases → Draft a new release**（首次可能显示 Create a new release）。
2. 新建标签 **`v1.3.0`**；Target 选择含最终源码和许可证的 `main` 提交。
3. 标题填 **`Mesh Axis Align v1.3.0`**。
4. 将 `docs/RELEASE-v1.3.0.md` 的正文粘贴到发布说明。
5. 在附件区域上传重新打包并验证过的 **`mesh_axis_align_v1.3.0.zip`**。
6. 先保存 Draft，检查附件、版本和 README；验证完成后发布。若仍希望收集早期反馈，可标记 **pre-release** 并在说明中明确。
7. 准备作为正式推荐版时，不勾选 pre-release，并按需要设置为 Latest，最后点击 **Publish release**。

GitHub 自动附带的 `Source code (zip)` / `Source code (tar.gz)` 是仓库源码快照；给 Blender 用户安装的是你上传的专用 ZIP。若启用 immutable releases，更应在草稿阶段把附件准备完整。[GitHub Release 官方流程](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

## 七、发布后核对

1. 使用未登录窗口打开仓库与 Release，确认确实能公开访问。
2. 从 GitHub 下载你上传的专用 ZIP，核对 SHA256，并再次试安装。
3. 给两份 README 增加下载入口。下面是模板，需把 `YOUR_USERNAME` 改为自己的 GitHub 用户名：

```markdown
[Download / 下载](https://github.com/YOUR_USERNAME/mesh-axis-align/releases/latest)
```

4. 确认 Issues 已启用；反馈模板可要求 Blender 版本、插件版本、按钮与设置、完整报告、最小复现对象。
5. 后续修复用新版本，例如 `1.3.1`，同步更新 `bl_info`、README、标签和 ZIP 名称。不要用同一版本号悄悄替换已经发布的不同代码。

## 八、可选：Git 命令行上传

网页上传与此方案二选一。此方案要求 Git 已安装、GitHub 已登录认证，并已创建**没有初始化 README/LICENSE 的空仓库**。若远端已存在文件，先 clone 再复制文件，不要强制推送覆盖。

在独立发布目录打开 PowerShell，先把下面用户名替换为你的实际账号：

```powershell
git init -b main
git add README.md README.zh-CN.md LICENSE .gitignore mesh_axis_align.py tests docs
git status
git commit -m "Prepare Mesh Axis Align v1.3.0 release"
git remote add origin https://github.com/YOUR_USERNAME/mesh-axis-align.git
git push -u origin main
```

然后按第六节通过网页创建标签和 Release。无需再手动创建同名 Git 标签。首次提交若提示身份未配置，按自己的姓名和提交邮箱设置 `git config user.name`、`git config user.email` 后重试。

## 发布前最后确认

- [ ] 公开维护者署名已确定。
- [ ] LICENSE 已补齐，README 和安装 ZIP 的许可信息一致。
- [ ] ZIP 中源码与最终标签指向的源码相同。
- [ ] 三个按钮的实际行为与中英文说明一致。
- [ ] 标明已验证环境及中文 UI，没有声称可修复法向/骨骼/原始材质。
- [ ] 下载附件是专用插件 ZIP，安装与撤销已验证。
- [ ] 发布内容仅包含这个工具需要的文件。
