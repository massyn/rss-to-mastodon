import yaml
import feedparser
import dateparser
import datetime
import requests
import re
import os

TAG_RE = re.compile(r'<[^>]+>')

def log(txt):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{ts} - {txt}")

def remove_tags(text):
    return TAG_RE.sub('', text)

def mastodon(action,msg = None):
    if action == 'post':
        log(f"Posting - {msg}")
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
            log("Posted...")

    if action == 'get':
        log("Reading Mastodon timeline...")
        r = requests.get(
            f"{os.environ['MASTODON_ENDPOINT']}/api/v1/timelines/home?limit=1",
            timeout=30,
            headers={
                'Authorization': f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"
                }
            )

        log(r.status_code)
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

    latest = dateparser.parse(x[0]['created_at'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : False})
    log(f"Latest timestamp from timeline is {latest}")

    with open(c,'rt') as y:
        cfg = yaml.safe_load(y)

        for rss in cfg['rss']:
            log(f"rss => {rss}")

            try:
                feed = feedparser.parse(rss, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
            except:
                feed = {}

            log(f"- Found {len(feed.get('entries',[]))} items...")

            for f in feed.get('entries',[]):
                #if (datetime.datetime.now(datetime.timezone.utc) - dateparser.parse(f['published'])) <= datetime.timedelta(hours=1):
                if dateparser.parse(f['published'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : False}) >= latest:
                    msg = f'''{feed['feed']['title']} - {f['title']})\n\n{remove_tags(f['summary'])}\n\n{f['link']}'''
                    mastodon('post',msg)
    
    log(" ** All done **")

if __name__=='__main__':
    main('config.yaml')