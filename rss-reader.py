import yaml
import feedparser
import dateparser
import datetime
import requests
import re

TAG_RE = re.compile(r'<[^>]+>')

def remove_tags(text):
    return TAG_RE.sub('', text)

def post_mastodon(msg,cfg):
    r = requests.post(
        f"{cfg['endpoint']}/api/v1/statuses",
        data={'status': msg},
        headers={'Authorization': f"Bearer {os.environ['MASTODON_ACCESS_TOKEN']}"})

    if r.status_code != 200:
        print(r.content)
    else:
        print("Posted...")

def main(c):
    with open(c,'rt') as y:
        cfg = yaml.safe_load(y)

        for rss in cfg['rss']:
            print(f"rss => {rss}")

            feed = feedparser.parse(rss)

            for f in feed['entries']:
                if (datetime.datetime.now(datetime.timezone.utc) - dateparser.parse(f['published'])) <= datetime.timedelta(hours=1):
                    msg = f'''{feed['feed']['title']} - {f['title']})\n\n{remove_tags(f['summary'])}\n\n{f['link']}'''
                    post_mastodon(msg,cfg['mastodon'])

if __name__=='__main__':
    main('config.yaml')