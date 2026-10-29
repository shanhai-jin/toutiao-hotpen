# 头条热笔（Toutiao HotPen）

> 从热点到成稿，自带合规闸门的今日头条/微头条推文创作技能。

「头条热笔」是一个面向 Agent（如 Claude/WorkBuddy 等）的创作类 Skill：多源抓取热点 → 交叉核实推选题 → 强制增量改写 → 微头条与头条长文双形态出稿 → 脚本自检（格式 + 去 AI 痕）→ 可选配图生产。**只产出草稿，不登录、不代发布。**

## 特性

- **双形态出稿**：微头条互动体（100-500 字）+ 头条长文观点体（800-1500 字，含导语）
- **强制增量节点**：热点改写先列 3 个常见角度，强制产出 ≥2 个增量角度，拒绝纯搬运
- **去 AI 痕自检**：自建高频套话库（命中即 FAIL）、连接词指纹、句长均匀度（低突发性）检测，对齐平台 AI 低质治理方向
- **防模板化**：叙事/数据/对话体三套骨架轮换 + 人设轮换
- **合规闸门**：信用分扣分对照、功效表述归属化、标题党红线（依据官方公开公告整理，以官方最新公告为准）
- **配图生产（可选）**：先提案后生成的三道关卡流程 + 版权与水印处理规范

## 安装

把整个 `toutiao-hotpen/` 目录放入你的 Agent skills 目录（WorkBuddy 为 `~/.workbuddy/skills/`），重载技能列表即可。也可以直接把 SKILL.md 内容作为系统提示词使用。

## 使用

```bash
# 多源热榜抓取（可选）
python scripts/fetch_hot.py 输出路径/hot_raw.json

# 成稿自检（出稿必跑，全绿才交付）
python scripts/check_article.py 成稿.txt           # 长文模式
python scripts/check_article.py --micro 成稿.txt   # 微头条模式
```

对 Agent 说：`推头条选题` / `追热点写条微头条` / `写篇头条文章` / `给这篇配图`。

首次使用：复制 `templates/accounts.example.json` 为 `accounts.json` 并填写署名与节奏参数。

## 目录结构

```
toutiao-hotpen/
├── SKILL.md                      # 技能主流程
├── references/
│   ├── writing-guide.md          # 双形态写作公式 + 强制增量
│   ├── deai-flavor.md            # 去 AI 痕五层自检
│   ├── compliance-toutiao.md     # 平台合规要点（引官方公开信息）
│   └── image-guide.md            # 配图生产（先提案后生成）
├── scripts/
│   ├── fetch_hot.py              # 多源热榜抓取（只读公开接口）
│   ├── check_article.py          # 双模式成稿自检
│   └── hotpen_cn_rules.py        # 汉字数字规则
└── templates/
    └── accounts.example.json     # 账号配置模板
```

## 免责声明

- 本技能仅辅助内容创作，发布请在平台后台人工操作，并遵守平台用户协议与声明义务
- 平台规则随时更新，`references/compliance-toutiao.md` 仅为公开信息整理，以官方最新公告为准
- 热榜接口为第三方公开服务，可用性不受本项目管理；接口变更请自行更新 `fetch_hot.py` 中的地址

## License

代码以 [MIT](LICENSE) 发布；`references/` 下的文档以 CC-BY-NC-4.0 发布（署名-非商业性使用）。
