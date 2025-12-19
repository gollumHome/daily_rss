import requests
import json
import os
import time
from datetime import datetime, timedelta

# ================= 配置区域 =================

NEWRANK_KEY = os.environ.get("NEWRANK_KEY")
WECOM_WEBHOOK_URL = os.environ.get("WECOM_WEBHOOK_URL")

TARGETS = [

    {"name": "每天打个新", "account": "gh_b2c2ad92da3f"},
    {"name": "终身投资者天威", "account": "gh_99505b0c4b83"},

]


# 4. 本地历史记录文件
HISTORY_FILE = "pushed_history.json"


# ===========================================

class WeChatNotifier:
    def __init__(self):
        self.webhook_url = WECOM_WEBHOOK_URL

    def send_text(self, news_list):
        """
        发送纯文本消息
        结构：来源 -> 标题 -> 摘要 -> 链接 -> 时间
        """
        if not self.webhook_url or not news_list:
            return

        # 构造消息头部
        content = f"📊 今日 IPO 深度日报 ({datetime.now().strftime('%m-%d')})\n"

        for item in news_list:
            # 清理一下摘要里的换行符，防止消息太乱
            clean_summary = item['summary'].replace('\n', ' ').strip()
            if len(clean_summary) > 100:
                clean_summary = clean_summary[:97] + "..."  # 摘要太长就截断

            content += f"------------------------------\n"
            content += f"📌 【{item['source']}】\n"
            content += f"📄 {item['title']}\n"
            content += f"💡 摘要: {clean_summary}\n"  # 这里用到了你强调的 summary
            content += f"🔗 {item['url']}\n"
            content += f"⏰ {item['time']}\n"

        payload = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                print("✅ 推送成功")
            else:
                print(f"❌ 推送失败: {resp.text}")
        except Exception as e:
            print(f"❌ 网络错误: {e}")


# ================= 数据获取逻辑 =================

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_history(history_list):
    # 保存最近500条
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_list[-500:], f, ensure_ascii=False, indent=2)


def get_articles(account_info):
    """
    根据你提供的官方示例，调用 /articles_content 接口
    必须带 from/to 时间参数
    """
    url = "https://api.newrank.cn/api/sync/weixin/account/articles_content"
    headers = {"Key": NEWRANK_KEY}

    # 自动生成最近 3 天的时间范围
    now = datetime.now()
    three_days_ago = now - timedelta(days=3)

    # 构造参数
    params = {
        "account": account_info['account'],
        "from": three_days_ago.strftime('%Y-%m-%d %H:%M:%S'),
        "to": now.strftime('%Y-%m-%d %H:%M:%S'),
        "page": "1",
        "size": "5"  # 一次取5条，管够
    }

    try:
        # 使用 data=params 发送表单数据
        resp = requests.post(url, headers=headers, data=params, timeout=15)
        res = resp.json()

        # 解析逻辑完全参考你提供的 JSON 结构
        if res.get('code') == 0:
            return res.get('data', [])
        else:
            print(f"⚠️ [{account_info['name']}] 接口报错: {res.get('msg')}")
            return []
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return []


# ================= 主程序 =================

if __name__ == "__main__":
    print("🚀 任务启动...")

    pushed_urls = load_history()
    new_items = []
    notifier = WeChatNotifier()

    for acc in TARGETS:
        print(f"🔍 检查: {acc['name']}...")
        articles_data = get_articles(acc)

        # 遍历 data 数组
        for item in articles_data:
            # 严格按照你提供的 JSON 字段提取
            title = item.get('title', '无标题')
            summary = item.get('summary', '无摘要')  # 提取 summary
            url = item.get('url', '')
            public_time = item.get('publicTime', '')

            # 去重逻辑
            if url in pushed_urls:
                continue

            # 简单过滤 (可选)：如果摘要和标题里都没有 IPO 相关的词，可能就不推
            # if "IPO" not in title and "新股" not in title: continue

            print(f"   🆕 发现: {title}")

            new_items.append({
                "source": acc['name'],
                "title": title,
                "summary": summary,  # 存入列表
                "url": url,
                "time": public_time
            })
            pushed_urls.append(url)

        time.sleep(1.5)  # 接口调用间隔

    if new_items:
        print(f"📨 准备推送 {len(new_items)} 条内容...")
        notifier.send_text(new_items)
        save_history(pushed_urls)
    else:
        print("😴 暂无新内容")