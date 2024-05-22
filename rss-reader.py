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

def mastodon(section,action,msg = None):
    endpoint = os.environ[f"{section}_ENDPOINT"]
    token = os.environ[f"{section}_ACCESS_TOKEN"]

    if action == 'post':
        log(f" - {section} - Posting - {msg}")
        r = requests.post(
            f"{endpoint}/api/v1/statuses",
            data={'status': msg},
            timeout=30,
            headers={ 'Authorization': f"Bearer {token}" }
        )
        
        if r.status_code != 200:
            print(r.content)
        else:
            log(f" - {section} - Posted...")

    if action == 'get':
        log(f" - {section} - Reading Mastodon timeline...")
        r = requests.get(
            f"{endpoint}/api/v1/timelines/home?limit=1",
            timeout=30,
            headers={ 'Authorization': f"Bearer {token}" }
        )

        log(f" - {section} - {r.status_code}")
        if r.status_code >= 200 and r.status_code < 300:
            return r.json()
        else:
            return []

def main(c):
    # Read the configuration
    try:
        with open(c,'rt') as y:
            cfg = yaml.safe_load(y)        
    except:
        log(f"Could not read {c} - ending...")
        exit(1)

    # Loop through each of the sections
    for section in cfg:
        log(f"Section ==> {section}")
        # -- find the latest post
        x = mastodon(section,'get')
        if len(x) == 0:
            # We do this so we can have a timestamp for the next run
            mastodon(section,'post','Welcome to the RSS Bot')
            exit(0)
        latest = dateparser.parse(x[0]['created_at'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : False})
        log(f" - {section} - Latest timestamp from timeline is {latest}")

        for rss in cfg[section]:
            log(f" - {section} - rss => {rss}")

            try:
                feed = feedparser.parse(rss, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
            except:
                feed = {}

            log(f" - {section} - Found {len(feed.get('entries',[]))} items...")
            for f in feed.get('entries',[]):
                #if (datetime.datetime.now(datetime.timezone.utc) - dateparser.parse(f['published'])) <= datetime.timedelta(hours=1):
                if dateparser.parse(f['published'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : False}) >= latest:
                    msg = f'''{feed['feed']['title']} - {f['title']})\n\n{remove_tags(f['summary'])}\n\n{f['link']}'''
                    mastodon(section,'post',msg)

    log(" ** All done **")

if __name__=='__main__':
    main('config.yaml')