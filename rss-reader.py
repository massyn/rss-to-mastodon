import yaml
import feedparser
import dateparser
import datetime
import requests
import re
import os

TAG_RE = re.compile(r'<[^>]+>')

def remove_tags(text):
    return TAG_RE.sub('', text)

def mastodon(action,msg = None):
    if action == 'post':
        print(f"Posting - {msg}")
        r = requests.post(
            f"{os.environ['MASTODON_ENDPOINT']}/api/v1/statuses",
            data={'status': msg},
            timeout=30,
            headers={
                'Authorization': f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
                }
            )
        
        if r.status_code != 200:
            print(r.content)
        else:
            print("Posted...")

    if action == 'get':
        r = requests.get(
            f"{os.environ['MASTODON_ENDPOINT']}/api/v1/timelines/home",
            timeout=30,
            headers={
                'Authorization': f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
                }
            )

        print(r.status_code)
        if r.status_code >= 200 and r.status_code < 300:
            return r.json()
        else:
            return []
        
def main(c):
    # -- find the latest post
    x = mastodon('get')
    if len(x) == 0:
        # We do this so we can have a timestamp for the next run
        mastodon('post','Welcome to the RSS Bot')
        exit(0)
    
    latest = dateparser.parse(x[0]['created_at'],settings={'TO_TIMEZONE': 'UTC'})

    with open(c,'rt') as y:
        cfg = yaml.safe_load(y)

        for rss in cfg['rss']:
            print(f"rss => {rss}")

            try:
                feed = feedparser.parse(rss, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
            except:
                feed = {}

            print(f"- Found {len(feed.get('entries',[]))} items...")

            for f in feed.get('entries',[]):
                #if (datetime.datetime.now(datetime.timezone.utc) - dateparser.parse(f['published'])) <= datetime.timedelta(hours=1):
                if dateparser.parse(f['published'],settings={'TO_TIMEZONE': 'UTC'}) >= latest:
                    msg = f'''{feed['feed']['title']} - {f['title']})\n\n{remove_tags(f['summary'])}\n\n{f['link']}'''
                    mastodon('post',msg)

if __name__=='__main__':
    main('config.yaml')