"""
Serenity (@aleabitoreddit) Twitter monitor - Render 持续运行版
每 60 秒检查一次，发现新推文立即推送微信 + QQ 邮件
"""
import os
import smtplib
import time
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from pathlib import Path

PUSHPLUS_TOKEN     = os.environ.get('PUSHPLUS_TOKEN', '')
QQ_EMAIL           = os.environ.get('QQ_EMAIL', '')
QQ_EMAIL_PASS      = os.environ.get('QQ_EMAIL_PASS', '')
_receivers_raw     = os.environ.get('QQ_EMAIL_RECEIVERS', '').strip()
QQ_EMAIL_RECEIVERS = _receivers_raw if _receivers_raw else QQ_EMAIL

TWITTER_USERNAME = 'aleabitoreddit'
LAST_ID_FILE     = '/tmp/serenity_last_id.txt'
CHECK_INTERVAL   = 60  # 秒

NITTER_INSTANCES = [
    'https://nitter.privacydev.net',
    'https://nitter.poast.org',
    'https://nitter.1d4.us',
    'https://nitter.lucahammer.com',
    'https://nitter.net',
]


def get_last_id():
    try:
        return Path(LAST_ID_FILE).read_text().strip()
    except FileNotFoundError:
        return ''


def set_last_id(tweet_id):
    Path(LAST_ID_FILE).write_text(str(tweet_id))


def get_latest_tweet():
    for instance in NITTER_INSTANCES:
        try:
            url = f'{instance}/{TWITTER_USERNAME}/rss'
            r = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; RSS reader/1.0)'
            })
            if r.status_code == 200 and '<item>' in r.text:
                root = ET.fromstring(r.text)
                channel = root.find('channel')
                if channel is not None:
                    item = channel.find('item')
                    if item is not None:
                        title    = item.findtext('title', '')
                        link     = item.findtext('link', '')
                        pub_date = item.findtext('pubDate', '')
                        tweet_id = link.rstrip('/').split('/')[-1].split('#')[0] if link else link
                        print(f'Nitter OK: {instance}', flush=True)
                        return {'id': tweet_id, 'text': title, 'link': link, 'published': pub_date}
        except Exception as e:
            print(f'Nitter {instance} failed: {e}', flush=True)
    return None


def push_wechat(title, content):
    if not PUSHPLUS_TOKEN:
        return
    try:
        requests.post('https://www.pushplus.plus/send', json={
            'token': PUSHPLUS_TOKEN, 'title': title,
            'content': content, 'template': 'markdown'
        }, timeout=10)
        print('微信推送成功', flush=True)
    except Exception as e:
        print(f'微信推送失败: {e}', flush=True)


def send_email(subject, body):
    if not QQ_EMAIL:
        return
    try:
        receivers = [r.strip() for r in QQ_EMAIL_RECEIVERS.split(',') if r.strip()]
        if not receivers:
            receivers = [QQ_EMAIL]
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = QQ_EMAIL
        msg['To']   = ', '.join(receivers)
        msg['Subject'] = subject
        with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=15) as s:
            s.login(QQ_EMAIL, QQ_EMAIL_PASS)
            s.sendmail(QQ_EMAIL, receivers, msg.as_string())
        print(f'邮件已发: {msg["To"]}', flush=True)
    except Exception as e:
        print(f'邮件失败: {e}', flush=True)


def check_once():
    tweet = get_latest_tweet()
    if not tweet:
        print('所有 Nitter 实例均失败，跳过', flush=True)
        return

    latest_id = tweet['id']
    last_id   = get_last_id()
    print(f'最新={latest_id}  上次={last_id}', flush=True)

    if latest_id == last_id:
        print('无新推文', flush=True)
        return

    set_last_id(latest_id)
    body = (
        f'Serenity 发布新推文\n\n'
        f'{tweet["text"]}\n\n'
        f'时间: {tweet["published"]}\n'
        f'链接: {tweet["link"]}'
    )
    push_wechat('Serenity新推文', body)
    send_email('Serenity新推文', body)
    print(f'推送完成: {tweet["text"][:80]}', flush=True)


def main():
    print(f'Serenity Monitor 启动，每 {CHECK_INTERVAL} 秒检查一次', flush=True)
    while True:
        try:
            check_once()
        except Exception as e:
            print(f'本轮出错: {e}', flush=True)
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
