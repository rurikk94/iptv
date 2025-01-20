import csv
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, fields
import os
from typing import List, Optional, Type, TypeVar
import requests
import asyncio
import aiohttp
import xmltodict
folder_path = "downloads"
if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print(f"Carpeta '{folder_path}' creada.")
# paw.patrol.247, 57532, S02E03, 20250119141500 -03:00
TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwYTcxNWQ3MzdlZThkNWQxOTFjMWMxYjljMzYyN2IyYyIsIm5iZiI6MTQ1NDM4NjgxOS4yMjgsInN1YiI6IjU2YjAyZTgyOTI1MTQxNTZiZTAwMDM4OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.l133MspoFtkD7W6Xj7_XGSQLXKFOcbJtrP6zflS05iY"

API_KEY= "0a715d737ee8d5d191c1c1b9c3627b2c"

LANGUAGE = "es-MX"

@dataclass
class CrewMember:
    job: str
    department: str
    credit_id: str
    adult: bool
    gender: Optional[int]
    id: int
    known_for_department: str
    name: str
    original_name: str
    popularity: float
    profile_path: Optional[str]

T = TypeVar('T', bound='Episode')

@dataclass
class Episode:
    air_date: str
    # crew: List[CrewMember] = field(default_factory=list)
    episode_number: int
    # guest_stars: List[dict] = field(default_factory=list)
    name: str
    overview: str
    id: int
    production_code: str
    runtime: int

    @classmethod
    def from_dict(cls: Type[T], data: dict) -> T:
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)

def dataclass_from_dict(klass, d):
    try:
        fieldtypes = {f.name:f.type for f in fields(klass)}
        return klass(**{f:dataclass_from_dict(fieldtypes[f],d[f]) for f in d})
    except:
        return d # Not a dataclass field

def obtener_canales247():
    file = "247.csv"
    canales = []
    with open(file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            canales.append((row['name'].strip(), row['tmdb-id'].strip(), row['episode'].strip(), row['time'].strip()))
    return canales

async def obtener_show_info_tmdb_async(tvshow, session):
    url = f"https://api.themoviedb.org/3/tv/{tvshow}?api_key={API_KEY}&language={LANGUAGE}"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
    return None

async def obtener_episode_info_tmdb_async(tvshow, season, episode, session):
    url = f"https://api.themoviedb.org/3/tv/{tvshow}/season/{season}/episode/{episode}?api_key={API_KEY}&language={LANGUAGE}"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
    return None

async def obtener_info_canales(canales):
    async with aiohttp.ClientSession() as session:
        shows = []
        for canal in canales:
            tasks = []
            name, tmdb_id, episode, time = canal
            time = datetime.strptime(time, "%Y%m%d%H%M%S %z")
            episode = episode.strip("S")
            season, episode = episode.split("E")
            tasks.append(obtener_episode_info_tmdb_async(tmdb_id, season, episode, session))
            tasks.append(obtener_show_info_tmdb_async(tmdb_id, session))

            results = await asyncio.gather(*tasks)
            show, episode = results[1], results[0]
            show["episode"] = episode
            show["start_at"] = time
            shows.append(show)
        return shows

canales = obtener_canales247()
shows = {}
results = asyncio.run(obtener_info_canales(canales))

for r in results:
    episode_info = r["episode"]
    show_info = r
    tmdb_id = r["id"]
    season, episode = episode_info["season_number"], episode_info["episode_number"]
    info = Episode.from_dict(episode_info)
    shows[tmdb_id] = {
        "name": show_info["name"],
        "episodes": show_info["number_of_episodes"],
        "episode": (season, episode),
        "start_at": show_info["start_at"],
        "info": show_info
    }

hasta = datetime.now(tz=timezone.utc) + timedelta(days=2)
async def obtener_lista_episodes(shows: dict):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for tmdb_id, v in shows.items():
            seasons = [s for s in v["info"]["seasons"]]
            seasons = [s for s in seasons if s["season_number"] > 0]
            episodes = [(s["season_number"], s["episode_count"]) for s in seasons]
            for season, count in episodes:
                for i in range(1, count + 1):
                    tasks.append(obtener_episode_info_tmdb_async(tmdb_id, season, i, session))

            results = await asyncio.gather(*tasks)
            v["episodes"] = results
    return shows

list_episodes = asyncio.run(obtener_lista_episodes(shows))


canales = []
programas = []

for idx, show in list_episodes.items():
    show_name = show["name"].replace(" ",".")
    canal = {'@id': show_name, 'display-name': {"#text":show_name,  "@lang":"es"}}
    s, e = show["episode"]
    start_at = show["start_at"]
    canales.append(canal)
    canales.append(canal)
    flag = False
    for episode in show["episodes"]:

        if (episode["season_number"] == s and episode["episode_number"] == e):
            flag = True

        if flag == False:
            continue

        stop = start_at + timedelta(minutes=episode["runtime"])
        programas.append({
            '@start': start_at.strftime("%Y%m%d%H%M%S %z"),
            '@stop': stop.strftime("%Y%m%d%H%M%S %z"),
            '@channel': show_name,
            'title': episode["name"],
            # "sub-title": episode["name"],
            'desc': episode["overview"],
            "epidosde-num": {
                "@system": "xmltv_ns",
                "#text": episode["production_code"]
            },
        })
        start_at = stop


epg = {
    'tv': {
        '@generator-info-name': 'XML Generated by tmmdb',
        'channel': canales,
        'programme': programas
    }
}
EPG_FILE_OUTPUT = f"{folder_path}/dragon_ball_epg.xml"
xmltodict.unparse(epg, output=open(EPG_FILE_OUTPUT, 'w', encoding="utf-8"), pretty=True)
