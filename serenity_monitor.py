import asyncio
import json
import os
import smtplib
import requests
from email.mime.text import MIMEText
from twikit import Client

GITHUB_TOKEN    = os.environ['GITHUB_TOKEN']
GITHUB_REPO     = os.environ['GITHUB_REPOSITORY']
TWITTER_COOKIES = os.environ['TWITTER_COOKIES']
PUSHPLUS_TOKEN  = os.environ.get('PUSHPLUS_TOKEN', '')
QQ_EMAIL        = os.environ.get('QQ_EMAIL', '')
QQ_EMAIL_PASS   = os.environ.get('QQ_EMAIL_PASS', '')

VAR_NAME = 'SERENITY_LAST_TWEET_ID'
HEADERS = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
}


def get_last_id():
    url = f'https://api.github.com/repos/{GITHUB_REPO}/actions/variables/{VAR_NAME}'
    r = requests.get(url, headers=HEADERS, timeout=10)
    return r.json().get('value', '') if r.status_code == 200 else ''


def set_last_id(tweet_id):
    base = f'https://api.github.com/repos/{GITHUB_REPO}/actions/variables'
    payload = {'name': VAR_NAME, 'value': str(tweet_id)}
    r = requests.patch(f'{base}/{VAR_NAME}', headers=HEADERS, json=payload, timeout=10)
    if r.status_code not in (200, 204):
        requests.post(base, headers=HEADERS, json=payload, timeout=10)


def push_wechat(title, content):
    if not PUSHPLUS_TOKEN:
        return
    try:
        requests.post(
            'https://www.pushplus.plus/send',
            json={'token': PUSHPLUS_TOKEN, 'title': title, 'content': content, 'template': 'markdown'},
            timeout=10,
        )
    except Exception as e:
        print(f'微信推送失败: {e}')


def send_email(subject, body):
    if not QQ_EMAIL:
        return
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = QQ_EMAIL
        msg['To'] = QQ_EMAIL
        msg['Subject'] = subject
        with smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=15) as s:
            s.login(QQ_EMAIL, QQ_EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print(f'邮件失败: {e}')


async def main():
    client = Client('en-US')
    client.set_cookies(json.loads(TWITTER_COOKIES))
    user = await client.get_user_by_screen_name('aleabitoreddit')
    tweets = await user.get_tweets('Tweets', count=1)
    if not tweets:
        print('未获取到推文')
        return
    latest = tweets[0]
    latest_id = str(latest.id)
    last_id = get_last_id()
    print(f'最新={latest_id}  上次={last_id}')
    if latest_id == last_id:
        print('无新推文')
        return
    set_last_id(latest_id)
    body = (
        f'**Serenity 发布新推文**\n\n'
        f'{latest.text}\n\n'
        f'---\n'
        f'时间: {latest.created_at}\n'
        f'链接: https://x.com/aleabitoreddit/status/{latest_id}'
    )
    push_wechat('Serenity新推文', body)
    send_email('Serenity新推文', body)
    print(f'推送成功: {latest.text[:80]}')


asyncio.run(main())
