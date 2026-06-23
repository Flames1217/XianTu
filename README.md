<p align="center">
  <img src="https://ddct.top/XianTu.png">
</p>

<table align="center">
  <tr>
    <td><img src="https://ddct.top/XianTu_black.png" width="400" alt="黑色主题"/></td>
    <td><img src="https://ddct.top/XianTu_light.png" width="400" alt="浅色主题"/></td>
  </tr>
</table>

<h1 align="center">仙途（Xian Tu）</h1>

<p align="center">
  <strong>AI 驱动的沉浸式修仙文字冒险游戏</strong>
</p>

<p align="center">
  <a href="https://qm.qq.com/q/mKtqgX0FSo">💬 QQ群：1079437686</a> •
  <a href="#功能概览">功能</a> •
  <a href="#技术栈">技术栈</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#许可证">许可证</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white" alt="Vue 3"/>
  <img src="https://img.shields.io/badge/TypeScript-blue?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/Pinia-yellow?style=flat-square&logo=vue.js&logoColor=white" alt="Pinia"/>
  <img src="https://img.shields.io/badge/Webpack-5-8DD6F9?style=flat-square&logo=webpack&logoColor=black" alt="Webpack"/>
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI-Gemini-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>
  <img src="https://img.shields.io/badge/AI-Claude-orange?style=flat-square&logo=anthropic&logoColor=white" alt="Claude"/>
  <img src="https://img.shields.io/badge/AI-OpenAI-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI"/>
  <img src="https://img.shields.io/badge/SillyTavern-兼容-purple?style=flat-square" alt="SillyTavern"/>
</p>

<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=qianye60.XianTu&left_color=gray&right_color=blue" alt="visitors"/>
  <img src="https://img.shields.io/github/stars/qianye60/XianTu?style=flat-square&color=yellow" alt="stars"/>
  <img src="https://img.shields.io/github/forks/qianye60/XianTu?style=flat-square" alt="forks"/>
</p>

<p align="center">
  <a href="https://qianye60.github.io/XianTu/游戏介绍.html">📖 游戏介绍</a> •
  <a href="https://www.ddct.top/">🎮 在线体验</a>
</p>

---

## 🌿 社区全栈增强版说明

本仓库基于 [qianye60/XianTu](https://github.com/qianye60/XianTu) 进行非商业二次开发，前端持续跟随原项目最新版，并以原项目 `v3.7.8` 曾公开的 FastAPI 后端为基础进行恢复、重构和兼容性补全。

相较原仓库当前仅提供前端的部署方式，本社区版重点补齐：

- 可自行部署的账号、登录、角色与云存档后端
- 在线状态、每日签到与穿越点
- 联机穿越、世界实例、邀请代码、地图操作、事件日志与世界快照
- 创意工坊、入侵报告和远程提示词配置
- SQLite 持久化、真实数据库健康检查和单镜像部署
- GitHub Actions 自动测试并发布 GHCR 镜像
- 面向 Northflank 等容器平台的完整部署方式

本仓库是独立维护的社区增强版，并非原作者的官方后端或官方服务。原项目名称、素材与版权归原作者及仙途项目组所有；使用和二次分发仍须遵守仓库中的 [LICENSE](./LICENSE)。

## ✨ 功能概览

🤖 **AI 动态叙事** — 支持 Gemini / Claude / OpenAI / DeepSeek 等多种大模型，实时生成个性化剧情

⚔️ **完整修仙体系** — 境界突破、三千大道、功法修炼、装备炼制、NPC 互动

🎲 **智能判定系统** — 基于境界、属性、装备、功法等多维度计算判定结果

💾 **多存档管理** — 多角色、多存档槽位，支持导入导出与云同步

🗺️ **开放世界** — 自由探索朝天大陆，触发奇遇事件，建立人物关系网络

📱 **全平台适配** — 完美支持桌面端与移动端，亮/暗双主题

🍺 **酒馆兼容** — 支持 SillyTavern 嵌入式环境与独立网页版

---

## 🛠️ 技术栈

|        前端        |        后端        |     AI     |
| :----------------: | :-----------------: | :---------: |
| Vue 3 + TypeScript |  Python + FastAPI  | Gemini API |
|   Pinia 状态管理   | SQLite / PostgreSQL | Claude API |
|     Vue Router     |      JWT 认证      | OpenAI API |
|      Webpack      |      WebSocket      | SillyTavern |
| Chart.js + Pixi.js |                    |  DeepSeek  |
|     IndexedDB     |                    |            |

---

## 🚀 快速开始

### Docker 部署（推荐）

```bash
docker run -d \
  --name xiantu \
  -p 8080:80 \
  -v xiantu-data:/data \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=请替换为稳定的随机密钥 \
  ghcr.io/flames1217/xiantu:latest
```

访问 http://localhost:8080 即可使用。

SQLite 数据保存在 `/data/xiantu.sqlite3`。不要运行多个共享同一 SQLite 文件的副本；需要横向扩容时请迁移到独立数据库。

### Northflank 部署

推荐使用 Git 仓库模式，让 Northflank 直接基于本仓库根目录的 `Dockerfile` 构建完整镜像。

1. 创建 Combined Service，部署来源选择 GitHub 仓库。
2. 选择仓库 `Flames1217/XianTu`，分支选择 `master`。
3. Build type 选择 Dockerfile，Dockerfile path 填写 `Dockerfile`，Build context 填写 `.`。
4. 添加公开 HTTP 端口 `80`。
5. 创建持久卷并挂载到 `/data`，实例数保持为 `1`。
6. 设置环境变量：

```env
ENVIRONMENT=production
SECRET_KEY=长度至少32位的稳定随机值
DDCT_DB_URL=sqlite:///data/xiantu.sqlite3
```

7. 健康检查路径填写 `/healthz`。

如需初始化管理账号，可在第一次启动时临时增加：

```env
CREATE_DEFAULT_ADMIN=true
DEFAULT_ADMIN_USERNAME=自定义管理员名
DEFAULT_ADMIN_PASSWORD=高强度密码
```

创建完成后建议删除这三个环境变量并重新部署。

如果只是临时快速验证，也可以使用已经发布的 GHCR 镜像：

```txt
ghcr.io/flames1217/xiantu:latest
```

### 本地开发

```bash
# 安装依赖
npm install

# 开发模式
npm run serve

# 生产构建
npm run build
```

## ☁️ 自动构建/部署

推送到 `master`、推送 `v*` 格式标签或手动运行工作流时自动触发：

- **完整测试**：前端类型检查、生产构建和后端契约测试
- **Docker 镜像**：构建并推送到 GitHub Container Registry
- **GitHub Release**：创建 Release 并上传构建产物 zip 包

```bash
git tag v3.7.0
git push origin v3.7.0
```

其他工作流：

- CI：`.github/workflows/ci.yml`（push/PR 自动 `type-check` + `build`）
- Pages：`.github/workflows/pages.yml`（push 到 `master` 自动部署到 GitHub Pages）

### 本地后端开发

后端用于提供账号、存档、联机穿越和创意工坊等 API，默认使用 SQLite。

```bash
pip install -r server/requirements.txt
set TURNSTILE_ENABLED=false
uvicorn server.main:app --reload --port 12345
```

环境变量配置见 `server/.env.example`

---

## 📖 更新日志

查看完整更新历史：[CHANGELOG.md](./CHANGELOG.md)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📄 许可证

本项目个人学习、研究免费使用。商业用途请先联系作者。

详见 [LICENSE](./LICENSE) | 联系方式：QQ 1538548527

---

## ☕ 支持项目

如果这个项目对你有帮助，欢迎赞助支持~

<p align="center">
  <img src="https://ddct.top/weixing.jpg" width="200" alt="微信赞助"/>
  <img src="https://ddct.top/zhifubao.jpg" width="200" alt="支付宝赞助"/>
</p>

---

<p align="center">
  <sub>如果觉得有帮助，请给个 ⭐ Star 支持一下！</sub>
</p>
