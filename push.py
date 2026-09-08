"""
简报推送模块
支持 Server酱（微信推送）和企业微信机器人。
在环境变量里配置对应 KEY 即可启用，不配则跳过。

  - Server酱:    设置 PUSH_KEY
  - 企业微信机器人: 设置 WECOM_KEY
"""
import os
import requests


def send_brief(content: str, title: str = "秋招雷达日报"):
    """把简报推送到已配置的渠道"""
    results = []

    # Server酱（微信）
    push_key = os.environ.get("PUSH_KEY", "").strip()
    if push_key:
        try:
            # Server酱正文上限约 32KB
            body = content[:30000]
            r = requests.post(
                f"https://sctapi.ftqq.com/{push_key}.send",
                data={"title": title, "desp": body},
                timeout=20,
            )
            resp = r.json()
            code = resp.get("code")
            data = resp.get("data", {})
            error = data.get("error", "")
            if code == 0 and error == "SUCCESS":
                results.append(f"Server酱: 成功 (pushid={data.get('pushid')})")
            else:
                results.append(f"Server酱: 接口返回非成功 code={code} error={error} resp={r.text[:200]}")
        except Exception as e:
            results.append(f"Server酱: 异常 {e}")

    # 企业微信机器人
    wecom_key = os.environ.get("WECOM_KEY", "").strip()
    if wecom_key:
        try:
            # 企业微信 markdown 消息上限 4096 字节，只发摘要
            summary = _extract_summary(content)
            r = requests.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={wecom_key}",
                json={
                    "msgtype": "markdown",
                    "markdown": {"content": summary[:4000]},
                },
                timeout=15,
            )
            ok = r.json().get("errcode") == 0
            results.append(f"企业微信: {'成功' if ok else '失败 ' + r.text[:100]}")
        except Exception as e:
            results.append(f"企业微信: 异常 {e}")

    if not results:
        print("未配置推送渠道（PUSH_KEY / WECOM_KEY），跳过推送。简报已保存到 reports/ 目录。")
    else:
        for r in results:
            print(f"  推送 {r}")


def _extract_summary(content: str) -> str:
    """从完整简报中提取摘要部分（总览 + 新增岗位）"""
    lines = content.split("\n")
    summary_lines = []
    capture = True
    for line in lines:
        summary_lines.append(line)
        # 截到"当前在招"之前
        if "当前在招" in line or "本次抓取到的存量岗位" in line:
            break
    return "\n".join(summary_lines)
