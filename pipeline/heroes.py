"""Collects game heroes from their publishers' own feeds: the official lore and blurbs, plus official art. Both
publishers let creators use their game content in monetized YouTube videos (Valve: store.steampowered.com/video_policy;
Riot: riotgames.com/legal-jibber-jabber); the assets are only used inside our videos, never redistributed on their own.
Resumable: files already on disk are kept.

Each game is a source with an alphabetical roster and a collect step that writes data/heroes/<game>/<key>/:
hero.json (name, lore, ...), and "reveal" art: a cut-out render (alpha) or a full splash picture.
The videos go through the games in GAMES order, each hero in alphabetical order (topic.py).

    heroes.py                 every hero of every game
    heroes.py dota2 pudge     one hero
"""
import re, sys, urllib.request
from common import *

DIR = ROOT / "data" / "heroes"  # under data/, so none of it goes into git


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "hikayat-ancient/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(html):
    """Feeds carry <b>, <br>, <p> and the like; the narration wants plain text."""
    return " ".join(re.sub(r"<[^>]+>", " ", html or "").replace("&nbsp;", " ").split())


def fetch_assets(d, assets):
    for name, url in assets.items():
        if not (d / name).exists():
            try:
                (d / name).write_bytes(get(url, timeout=120))
            except Exception as e:  # noqa: BLE001 - a hero without one asset is still usable
                log(d.name, name, "missing:", str(e)[:120])
            time.sleep(0.5)


class Dota2:
    key, name, owner, query = "dota2", "Dota 2", "Valve Corporation", "dota 2"
    hashtags = "#dota2 #lorehero #dota2indonesia"
    FEED = "https://www.dota2.com/datafeed/{what}?language=english"
    CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2"
    ATTR = {0: "strength", 1: "agility", 2: "intelligence", 3: "universal"}

    def roster(self):
        """[(key, display name)] in alphabetical order."""
        heroes = json.loads(get(self.FEED.format(what="herolist")))["result"]["data"]["heroes"]
        self._ids = {h["name"].removeprefix("npc_dota_hero_"): h["id"] for h in heroes}
        return sorted(((h["name"].removeprefix("npc_dota_hero_"), h["name_loc"]) for h in heroes),
                      key=lambda x: x[1].lower())

    def collect(self, key):
        d = DIR / self.key / key
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "hero.json").exists():
            if not getattr(self, "_ids", None):
                self.roster()
            for n in range(4):  # the feed sometimes answers {"result": null} when asked too often
                r = json.loads(get(self.FEED.format(what="herodata") + f"&hero_id={self._ids[key]}")).get("result")
                if r:
                    break
                time.sleep(10 * (n + 1))
            else:
                log(key, "no data from the feed; skipped")
                return None
            x = r["data"]["heroes"][0]
            save(d / "hero.json", {
                "game": self.name, "key": key, "name": x["name_loc"],
                "attribute": self.ATTR.get(int(x.get("primary_attr", -1)), "?"),
                "lore": clean(x.get("bio_loc")), "hype": clean(x.get("hype_loc")), "summary": clean(x.get("npe_desc_loc")),
                "abilities": [{"name": a.get("name_loc"), "text": clean(a.get("desc_loc"))}
                              for a in x.get("abilities", []) if a.get("name_loc") and not a.get("ability_is_innate")][:6],
                "reveal": "render.png", "source": "dota2.com datafeed (Valve)"})
            time.sleep(0.5)
        fetch_assets(d, {"portrait.png": f"{self.CDN}/images/dota_react/heroes/{key}.png",
                         "render.png": f"{self.CDN}/videos/dota_react/heroes/renders/{key}.png",
                         "render.webm": f"{self.CDN}/videos/dota_react/heroes/renders/{key}.webm"})
        return d


class LeagueOfLegends:
    key, name, owner, query = "lol", "League of Legends", "Riot Games", "league of legends"
    hashtags = "#leagueoflegends #lolindonesia #lorechampion"
    DD = "https://ddragon.leagueoflegends.com"
    UNIVERSE = "https://universe-meeps.leagueoflegends.com/v1/en_us/champions/{slug}/index.json"

    def roster(self):
        ver = json.loads(get(f"{self.DD}/api/versions.json"))[0]
        champs = json.loads(get(f"{self.DD}/cdn/{ver}/data/en_US/champion.json"))["data"]
        self._ver = ver
        return sorted(((c["id"], c["name"]) for c in champs.values()), key=lambda x: x[1].lower())

    def collect(self, key):
        d = DIR / self.key / key
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "hero.json").exists():
            if not getattr(self, "_ver", None):
                self.roster()
            c = json.loads(get(f"{self.DD}/cdn/{self._ver}/data/en_US/champion/{key}.json"))["data"][key]
            lore = c.get("lore", "")
            try:  # the Universe site has the full biography; Data Dragon only a short one
                u = json.loads(get(self.UNIVERSE.format(slug=key.lower())))
                lore = clean(u["champion"]["biography"]["full"]) or lore
            except Exception as e:  # noqa: BLE001
                log(key, "no Universe biography, using the short lore:", str(e)[:120])
            save(d / "hero.json", {
                "game": self.name, "key": key, "name": c["name"], "title": c.get("title"),
                "lore": clean(lore), "summary": clean(c.get("blurb")), "tags": c.get("tags", []),
                "abilities": [{"name": s["name"], "text": clean(s["description"])} for s in c.get("spells", [])][:4],
                "reveal": "splash.jpg", "source": "Riot Data Dragon + Universe"})
            time.sleep(0.5)
        fetch_assets(d, {"splash.jpg": f"{self.DD}/cdn/img/champion/splash/{key}_0.jpg",
                         "portrait.jpg": f"{self.DD}/cdn/img/champion/loading/{key}_0.jpg"})
        return d


GAMES = [Dota2(), LeagueOfLegends()]
BY_KEY = {g.key: g for g in GAMES}


def main(game=None, only=None):
    for g in GAMES:
        if game and g.key != game:
            continue
        roster = g.roster()
        if only:
            roster = [r for r in roster if r[0] in only]
        for n, (key, _) in enumerate(roster, 1):
            g.collect(key)
            time.sleep(1)
            if n % 10 == 0 or n == len(roster):
                log(f"{g.name}: {n}/{len(roster)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None, set(sys.argv[2:]) or None)
