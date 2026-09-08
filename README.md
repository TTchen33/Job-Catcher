# Job-Catcher · 香港 / 深圳岗位雷达

每天检查招聘来源，对比历史岗位，生成香港和深圳的岗位日报。
基于 [ruyi1/campus-radar](https://github.com/ruyi1/campus-radar)，原始版本为 `80f4289`；原项目说明保存在 [UPSTREAM_README.md](UPSTREAM_README.md)。

## 查看结果

- [最新日报](reports/latest.md)
- [每日运行记录](https://github.com/TTchen33/Job-Catcher/actions/workflows/daily.yml)
- 历史日报保存在 `reports/YYYY-MM-DD.md`，抓取状态保存在 `reports/latest.json`。

## 当前规则

- 香港、Hong Kong、Hongkong、HK、深圳、Shenzhen 均可匹配，不区分英文大小写。
- 暂不限制岗位方向；原来的电商、产品、运营关键词仍保留，可在 `config.py` 中开启。
- 地点为空、全国或多地的岗位保留，投递前需确认是否开放香港或深圳。
- 内置来源：京东、快手、小红书、拼多多、淘宝、OfferStar。
- 这些来源主要覆盖内地校招。城市筛选并不等于已覆盖香港本地雇主；后续按提供的官网链接增加来源。
- 每日香港时间 / 北京时间 09:00 运行；GitHub 排队可能造成延迟。
- 第一次运行只建立当前岗位基线，之后才将新发现的岗位列为新增。
- 抓取失败单独列出并使自动任务报错；其他成功来源仍保存结果。

## 以后添加网站

把招聘列表链接提供给维护者，并说明公司名称、希望筛选的条件。公开 JSON 接口可以接入 `config.py` 的 `GENERIC_SOURCES`；通用 HTML 模式目前只支持表格。动态渲染、特殊分页或卡片页面需要专用抓取器。

接入后先验证岗位 ID、分页、地点和详情链接，再加入每日任务。仅记录首次发现和最近出现时间，当前不提供可靠的下架、截止日期变化或内容修改提醒。

## 通知

默认把结果保存在仓库，不依赖微信配置。若需要微信推送，在仓库 **Settings → Secrets and variables → Actions** 添加 `PUSH_KEY`（Server酱）或 `WECOM_KEY`（企业微信机器人）。密钥只填入 Secrets，不写入代码、Issue 或日报。

已配置渠道时，有新增目标岗位或抓取异常才推送；正常无新增时保持安静。

## 本地运行

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py --no-push
```

`main.py` 自动判断是否为首次运行。`--strict` 在来源失败时返回非零状态。`--full` 仅允许空数据库初始化，不会清除已有历史。

## 个人投递记录

`tracker.py` 的添加、更新和导出功能保留，记录独立保存到 `data/applications.db`，该文件和导出的个人表格默认忽略，不进入 Git 版本库。公开日报默认不包含个人投递记录。

```bash
python tracker.py add
python tracker.py list
python tracker.py export
```

## 自动运行

工作流位于 `.github/workflows/daily.yml`。部署代码或更改抓取配置时会运行一次，也可在 Actions 页面使用 **Run workflow** 手动运行。任务串行执行，并将岗位数据库和日报提交回 `main` 分支。
