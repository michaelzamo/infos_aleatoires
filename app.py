from flask import Flask, jsonify, render_template_string, request
import feedparser
import random
import os
import json

app = Flask(__name__)

SAVED_FILE = 'saved_links.txt'

# --- GESTION DES FLUX ---
def load_feeds_config():
    feeds_data = {}
    current_category = None
    try:
        with open('feeds.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1]
                    feeds_data[current_category] = []
                elif current_category:
                    feeds_data[current_category].append(line)
    except FileNotFoundError:
        return {"Défaut": ["https://www.lemonde.fr/rss/une.xml"]}
    return feeds_data

# --- GESTION DES SAUVEGARDES ---
def get_saved_links(category_filter=None):
    links = []
    if not os.path.exists(SAVED_FILE):
        return links
    try:
        with open(SAVED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split('|')
                
                if len(parts) == 2:
                    cat, url, title = "Général", parts[0], parts[1]
                elif len(parts) >= 3:
                    cat = parts[0]
                    url = parts[1]
                    title = "|".join(parts[2:])
                else:
                    continue

                if category_filter and cat != category_filter:
                    continue
                    
                links.append({'category': cat, 'url': url, 'title': title})
    except Exception as e:
        print(f"Erreur lecture sauvegarde: {e}")
    return links

def save_link_to_file(category, url, title):
    current_links = get_saved_links()
    for link in current_links:
        if link['url'] == url:
            return False 
    
    with open(SAVED_FILE, 'a', encoding='utf-8') as f:
        clean_title = title.replace('\n', ' ').replace('\r', '')
        f.write(f"{category}|{url}|{clean_title}\n")
    return True

def delete_link_from_file(url_to_delete):
    if not os.path.exists(SAVED_FILE): return False
    lines_to_keep = []
    deleted = False
    
    with open(SAVED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            current_url = parts[0] if len(parts) == 2 else parts[1] if len(parts) >= 3 else ""
            if current_url == url_to_delete:
                deleted = True
            else:
                lines_to_keep.append(line)
    
    with open(SAVED_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines_to_keep)
    return deleted

@app.route('/')
def home():
    feeds_config = load_feeds_config()
    categories = list(feeds_config.keys())
    if not categories: categories = ["Aucune catégorie"]

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Info Aléatoire</title>
        <style>
            /* --- VARIABLES --- */
            :root {
                --font-scale: 1;
                --bg-body: #f0f2f5; --bg-card: #ffffff;
                --text-main: #333; --text-sub: #666;
                --tag-bg: #e9ecef; --select-bg: #f9f9f9; --select-border: #ddd;
                --shadow: 0 10px 25px rgba(0,0,0,0.05);
                --col-primary: #007bff; --col-success: #28a745; --col-error: #dc3545; --col-link-read: #28a745;
                --col-save: #6c757d;
                --border-rad: 16px;
            }
            
            body.dark-mode {
                --bg-body: #121212; --bg-card: #1e1e1e;
                --text-main: #e0e0e0; --text-sub: #aaaaaa;
                --tag-bg: #333; --select-bg: #2c2c2c; --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }

            /* PROFILS DALTONISME */
            body.protanopia, body.deuteranopia { --col-primary: #0072B2; --col-success: #56B4E9; --col-error: #D55E00; --col-link-read: #0072B2; }
            body.tritanopia { --col-primary: #000000; --col-success: #009E73; --col-error: #CC79A7; --col-link-read: #009E73; }
            body.achromatopsia { --col-primary: #000000; --col-success: #000000; --col-error: #000000; --col-link-read: #444444; }
            body.dark-mode.achromatopsia { --col-primary: #ffffff; --col-success: #ffffff; --col-error: #ffffff; --col-link-read: #dddddd; }

            /* STYLES GÉNÉRAUX */
            body { 
                font-family: "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                display: flex; justify-content: center; align-items: center; 
                min-height: 100vh;
