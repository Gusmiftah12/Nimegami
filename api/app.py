from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import base64
import re
import random
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
]

# Custom aiohttp connector to limit requests per domain and total concurrent requests
conn = aiohttp.TCPConnector(limit_per_host=5, limit=10)

@app.get("/")
async def health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)

async def fetch_anime_data(query):
    url = f"https://nimegami.id/?s={query}&post_type=post"
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://nimegami.id/'
        }
        async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                results = []
                for article in soup.find_all('article'):
                    title_element = article.find('h2', itemprop="name").find('a')
                    title = title_element.text.strip() if title_element else "N/A"
                    anime_url = title_element['href'] if title_element else "N/A"

                    image_element = article.select_one('.thumbnail img')
                    image = image_element['src'] if image_element else "No image available"

                    status_element = article.select_one('.term_tag-a a')
                    status = status_element.text.strip() if status_element else "N/A"

                    type_element = article.select_one('.terms_tag a')
                    type = type_element.text.strip() if type_element else "N/A"

                    rating_element = article.select_one('.rating-archive i')
                    rating = rating_element.next_sibling.strip() if rating_element else "N/A"

                    episodes_element = article.select_one('.eps-archive')
                    episodes = episodes_element.text.strip() if episodes_element else "N/A"

                    results.append({
                        'title': title,
                        'image': image,
                        'status': status,
                        'type': type,
                        'rating': rating,
                        'episodes': episodes,
                        'anime_url': anime_url
                    })

                return results

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {e}")

async def fetch_anime_details(anime_url):
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://nimegami.id/'
        }
        async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
            async with session.get(anime_url) as response:
                response.raise_for_status()
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                details = {}

                details.update(fetch_basic_anime_info(soup))

                details['sinopsis'] = fetch_synopsis(soup)

                details['img'] = fetch_image_url(soup)

                details['episodes'] = fetch_episode_info(soup)

                details['batch_downloads'] = fetch_batch_downloads(soup)

                details['episode_downloads'] = fetch_episode_downloads(soup)

                return details

    except aiohttp.ClientError as e:
        logging.error(f"Network error: {e}")
        raise HTTPException(status_code=500, detail=f"Network error: {e}")

def fetch_basic_anime_info(soup):
    details = {}
    info_div = soup.find('div', class_='info2')
    if not info_div:
        raise HTTPException(status_code=404, detail="Informasi anime tidak ditemukan.")
    
    table_rows = info_div.find('table').find_all('tr')
    for row in table_rows:
        key_element = row.find('td', class_='tablex')
        value_element = row.find_all('td')[1]

        if key_element and value_element:
            key = key_element.text.strip().replace(':', '')
            value = parse_table_value(key, value_element)
            details[key] = value
    return details

def parse_table_value(key, value_element):
    if key == 'Kategori':
        return [a.text.strip() for a in value_element.find_all('a')]
    elif key in ['Musim / Rilis', 'Type', 'Series']:
        return value_element.find('a').text.strip()
    else:
        return value_element.text.strip()

def fetch_synopsis(soup):
    synopsis_div = soup.find('div', itemprop='text', id='Sinopsis')
    if not synopsis_div:
        return "Sinopsis tidak ditemukan."
    
    synopsis_paragraph = synopsis_div.find('p', recursive=False)
    return synopsis_paragraph.text.strip() if synopsis_paragraph else ""

def fetch_image_url(soup):
    image_element = soup.select_one('.thumbnail img')
    return image_element['src'] if image_element else ""

def fetch_episode_info(soup):
    episode_list = soup.select('.list_eps_stream li')
    episodes = []
    for episode_item in episode_list:
        episode_title = episode_item.get('title', '')
        episode_id = episode_item.get('id')
        episode_title = parse_episode_title(episode_id, episode_title)

        episode_data = json.loads(base64.b64decode(episode_item['data']).decode('utf-8'))
        streaming_urls = parse_streaming_urls(episode_data)

        episodes.append({
            'title': episode_title,
            'streaming_urls': streaming_urls,
            'id': episode_id
        })
    return episodes

def parse_episode_title(episode_id, default_title):
    episode_map = {
        "play_eps_1": "Episode 1",
        "play_eps_2": "Episode 2",
        "play_eps_3": "Episode 3"
    }
    return episode_map.get(episode_id, default_title)

def parse_streaming_urls(episode_data):
    streaming_urls = {}
    for data_dict in episode_data:
        if 'format' in data_dict:
            format_key = data_dict['format']
            if 'url' in data_dict and data_dict['url']:
                streaming_urls[format_key] = data_dict['url'][0]
    return streaming_urls

def fetch_batch_downloads(soup):
    download_box = soup.find('div', class_='download_box')
    batch_downloads = {}
    if download_box:
        batch_list = download_box.find('ul')
        if batch_list:
            for li in batch_list.find_all('li'):
                resolution, links = li.text.split(' ', 1)
                batch_downloads[resolution] = [a['href'] for a in li.find_all('a')]
    return batch_downloads

def fetch_episode_downloads(soup):
    episode_downloads = {}
    for h4 in soup.find_all('h4'):
        episode_title = h4.text.strip()
        download_list = h4.find_next_sibling('ul')
        if download_list:
            episode_downloads[episode_title] = {}
            for a_tag in download_list.find_all('a'):
                title = a_tag.get('title')
                if title:
                    resolution_match = re.search(r'(\d+p)', title)
                    if resolution_match:
                        resolution = resolution_match.group(1)
                        link_name = a_tag.text.strip()
                        link = a_tag['href']
                        if resolution not in episode_downloads[episode_title]:
                            episode_downloads[episode_title][resolution] = {}
                        episode_downloads[episode_title][resolution][link_name] = link
    return episode_downloads

@app.get("/search")
async def search_anime(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    results = await fetch_anime_data(query)
    return JSONResponse(content=results)

@app.get("/details")
async def anime_details(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    details = await fetch_anime_details(url)
    return JSONResponse(content=details)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
