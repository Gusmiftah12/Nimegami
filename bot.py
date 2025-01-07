from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import requests
import json
import random
import string

API_ID = "961780"
API_HASH = "bbbfa43f067e1e8e2fb41f334d32a6a7"
BOT_TOKEN = "5219568853:AAGLyw56AsFYsGkCKP2Q3keZRgYB_JwKkTE"

app = Client("anime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory storage for callback data
callback_data_storage = {}

def generate_callback_data():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

@app.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("Welcome! Use /search <anime name> to find anime.")

@app.on_message(filters.command("search"))
def search(client, message):
    if len(message.command) < 2:
        message.reply_text("Please provide an anime name to search.")
        return
    
    query = ' '.join(message.command[1:])
    response = requests.get('https://academic-cal-booogd-ea0d3f67.koyeb.app/search', params={'query': query})
    results = response.json()
    
    if not results:
        message.reply_text("No results found.")
        return
    
    keyboard = []
    for result in results:
        callback_data = generate_callback_data()
        callback_data_storage[callback_data] = result['anime_url']
        keyboard.append([InlineKeyboardButton(result['title'], callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message.reply_text("Select an anime:", reply_markup=reply_markup)

@app.on_callback_query()
def button(client, callback_query):
    callback_data = callback_query.data
    anime_url = callback_data_storage.get(callback_data)
    
    if not anime_url:
        callback_query.answer("Invalid selection.", show_alert=True)
        return
    
    response = requests.get('https://academic-cal-booogd-ea0d3f67.koyeb.app/details', params={'url': anime_url})
    details = response.json()
    
    formatted_details = format_anime_details(details)
    callback_query.message.edit_text(formatted_details)

def format_anime_details(details):
    formatted = ""
    
    formatted += f"Title: {details.get('Judul ', 'N/A')}\n"
    formatted += f"Alternative Title: {details.get('Judul Alternatif ', 'N/A')}\n"
    formatted += f"Duration: {details.get('Durasi Per Episode ', 'N/A')}\n"
    formatted += f"Rating: {details.get('Rating ', 'N/A')}\n"
    formatted += f"Studio: {details.get('Studio ', 'N/A')}\n"
    formatted += f"Categories: {details.get('Kategori ', 'N/A')}\n"
    formatted += f"Season/Release: {details.get('Musim / Rilis ', 'N/A')}\n"
    formatted += f"Type: {details.get('Type ', 'N/A')}\n"
    formatted += f"Series: {details.get('Series ', 'N/A')}\n"
    formatted += f"Subtitle: {details.get('Subtitle ', 'N/A')}\n"
    formatted += f"Credit: {details.get('Credit ', 'N/A')}\n"
    formatted += f"\nSynopsis: {details.get('sinopsis', 'N/A')}\n"
    formatted += f"\nImage: {details.get('img', 'No image available')}\n"
    
    formatted += "\nEpisodes:\n"
    if details.get('episodes'):
        for episode in details['episodes']:
            formatted += f"  - {episode['title']}\n"
            for resolution, url in episode.get('streaming_urls', {}).items():
                formatted += f"    {resolution}: {url}\n"
    else:
        formatted += "  No episodes available.\n"

    formatted += "\nBatch Downloads:\n"
    if details.get('batch_downloads'):
        for resolution, links in details['batch_downloads'].items():
            formatted += f"  {resolution}:\n"
            for link in links:
                formatted += f"    {link}\n"
    else:
        formatted += "  No batch downloads available.\n"

    formatted += "\nEpisode Downloads:\n"
    if details.get('episode_downloads'):
        for episode_title, resolutions in details['episode_downloads'].items():
            formatted += f"  {episode_title}:\n"
            for resolution, links in resolutions.items():
                formatted += f"    {resolution}:\n"
                for link_name, link in links.items():
                    formatted += f"      {link_name}: {link}\n"
    else:
        formatted += "  No episode downloads available.\n"

    return formatted

if __name__ == "__main__":
    app.run()
