"""
Serenity (@aleabitoreddit) Twitter monitor
Uses Nitter RSS — no API keys or cookies needed
"""
import json
import os
import smtplib
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText

GITHUB_TOKEN       = os.environ['GITHUB_TOKEN']
GITHUB_REPO        = os.environ['GITHUB_REPOSITORY']
PUSHPLUS_TOKEN     = os.environ.get('PUSHPLUS_TOKEN', '')
QQ_EMAIL           = os.environ.get('QQ_EMAIL', '')
QQ_EMAIL_PASS      = os.environ.get('QQ_EMAIL_PASS', '')
# 多收件人：逗号分隔，不填则默认发给 QQ_EMAIL 自己
QQ_EMAIL_RECEIVERS = os.environ.get('QQ_EMAIL_RECEIVERS', QQ_EMAIL)

TWITTER_USERNAME = 'aleabitoreddit'
VAR_NAME = 'SERENITY_LAST_TWEET_ID'

GH_HEADERS = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
}

NITTER_INSTANCES = [
    'https://nitter.privacydev.net',
    'https://nitter.poast.org',
    'https://nitter.1d4.us',
    'https://nitter.lucahammer.com',
    'https://nitter.net',
]


def get_last_id():
    url = f'https://api.github.com/repos/{GITHUB_REPO}/actions/variables/{VAR_NAME}'
    r = requests.get(url, headers=GH_HEADERS, timeout=10)
    return r.json().get('value', '') if r.status_code == 200 else ''


def set_last_id(tweet_id):
    base = f'https://api.github.com/repos/{GITHUB_REPO}/actions/variables'
    payload = {'name': VAR_NAME, 'value': str(tweet_id)}
    r = requests.patch(f'{base}/{VAR_NAME}', headers=GH_HEADERS, json=payload, timeout=10)
    if r.status_code not in (200, 204):
        requests.post(base, headers=GH_HEADERS, json=payload, timeout=10)


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
                        print(f'Nitter OK: {instance}')
                        return {'id': tweet_id, 'text': title, 'link': link, 'published': pub_date}
        except Exception as e:
            print(f'Nitter {instance} failed: {e}')
    return None


def push_wechat(title, content):
    if not PUSHPLUS_TOKEN:
        return
    try:
        requests.post('https://www.pushplus.plus/send', json={
            'token': PUSHPLUS_TOKEN, 'title': title,
            'content': content, 'template': 'markdown'
        }, timeout=10)
    except Exception as e:
        print(f'微信推送失败: {e}')


def send_email(subject, body):
    if not QQ_EMAIL:
        return
    try:
        receivers = [r.strip() for r in QQ_EMAIL_RECEIVERS.split(',') if r.strip()]
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = QQ_EMAIL
        msg['To'] = ', '.join(receivers)
        msg['Subject'] = subject
        with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=15) as s:
            s.login(QQ_EMAIL, QQ_EMAIL_PASS)
            s.sendmail(QQ_EMAIL, receivers, msg.as_string())
        print(f'邮件已发送给: {msg["To"]}')
    except Exception as e:
        print(f'邮件失败: {e}')


def main():
    tweet = get_latest_tweet()
    if not tweet:
        print('所有 Nitter 实例均失败，本次跳过')
        return

    latest_id = tweet['id']
    last_id   = get_last_id()
    print(f'最新={latest_id}  上次={last_id}')

    if latest_id == last_id:
        print('无新推文')
        return

    set_last_id(latest_id)

    body = (
        f'**Serenity 发布新推文**\n\n'
        f'{tweet["text"]}\n\n'
        f'---\n'
        f'时间: {tweet["published"]}\n'
        f'链接: {tweet["link"]}'
    )
    push_wechat('Serenity新推文', body)
    send_email('Serenity新推文', body)
    print(f'推送成功: {tweet["text"][:80]}')


main()
