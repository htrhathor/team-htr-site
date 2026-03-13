import os
import requests
import sqlite3
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

# ======================================
# CONFIG TWITCH
# ======================================
CLIENT_ID = "ww0hw9c3eqny316rd74pt93waji2qr"
CLIENT_SECRET = "0r0ugzlp2p1t0v7tyuhnqi2ghuk3w8"
REDIRECT_URI = "https://team-htr-site.onrender.com/callback"  # HTTPS obligatoire pour Twitch

# ======================================
# INIT APP
# ======================================
app = Flask(__name__)
CORS(app)

# ======================================
# DATABASE USERS
# ======================================
users_db = sqlite3.connect("users.db", check_same_thread=False)
users_cursor = users_db.cursor()
users_cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    twitch_id TEXT PRIMARY KEY,
    username TEXT,
    viewer INTEGER,
    channel INTEGER,
    streamer INTEGER,
    owner INTEGER
)
""")
users_db.commit()

# ======================================
# DATABASE WARNS
# ======================================
warn_db = sqlite3.connect("warns.db", check_same_thread=False)
warn_cursor = warn_db.cursor()
warn_cursor.execute("""
CREATE TABLE IF NOT EXISTS warns(
    username TEXT PRIMARY KEY,
    warns INTEGER
)
""")
warn_db.commit()

# ======================================
# GET TWITCH APP TOKEN
# ======================================
def get_token():
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    r = requests.post(url, params=params)
    r.raise_for_status()
    return r.json()["access_token"]

# ======================================
# LOGIN TWITCH
# ======================================
@app.route("/login")
def login():
    url = (
        f"https://id.twitch.tv/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=user:read:email"
    )
    return redirect(url)

# ======================================
# CALLBACK TWITCH
# ======================================
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code provided"}), 400

    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    r = requests.post(url, params=params)
    r.raise_for_status()
    access_token = r.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID
    }

    user_data = requests.get("https://api.twitch.tv/helix/users", headers=headers).json()
    user = user_data["data"][0]
    twitch_id = user["id"]
    username = user["login"]

    users_cursor.execute("SELECT * FROM users WHERE twitch_id=?", (twitch_id,))
    existing = users_cursor.fetchone()

    if not existing:
        users_cursor.execute(
            "INSERT INTO users VALUES (?, ?, 1, 0, 0, 0)",
            (twitch_id, username)
        )
        users_db.commit()

    return jsonify({"username": username, "message": "login successful"})

# ======================================
# USER LIST
# ======================================
@app.route("/users")
def users():
    users_cursor.execute("SELECT * FROM users")
    rows = users_cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "username": row[1],
            "viewer": row[2],
            "channel": row[3],
            "streamer": row[4],
            "owner": row[5]
        })
    return jsonify(result)

# ======================================
# UPDATE USER ROLE
# ======================================
@app.route("/setrole")
def set_role():
    username = request.args.get("user")
    viewer = int(request.args.get("viewer", 0))
    channel = int(request.args.get("channel", 0))
    streamer = int(request.args.get("streamer", 0))
    owner = int(request.args.get("owner", 0))

    users_cursor.execute(
        "UPDATE users SET viewer=?, channel=?, streamer=?, owner=? WHERE username=?",
        (viewer, channel, streamer, owner, username)
    )
    users_db.commit()
    return jsonify({"status": "updated"})

# ======================================
# WARN USER
# ======================================
@app.route("/warn")
def warn_user():
    user = request.args.get("user")
    warn_cursor.execute("SELECT warns FROM warns WHERE username=?", (user,))
    result = warn_cursor.fetchone()

    if not result:
        warn_cursor.execute("INSERT INTO warns VALUES (?, 1)", (user,))
        warn_db.commit()
        return jsonify({"warns": 1})

    warns = result[0] + 1
    warn_cursor.execute("UPDATE warns SET warns=? WHERE username=?", (warns, user))
    warn_db.commit()
    return jsonify({"warns": warns})

# ======================================
# WARN STATS
# ======================================
@app.route("/stats")
def stats():
    warn_cursor.execute("SELECT * FROM warns")
    rows = warn_cursor.fetchall()
    result = [{"viewer": row[0], "warns": row[1]} for row in rows]
    return jsonify(result)

# ======================================
# LIVE STATUS
# ======================================
@app.route("/live")
def live_status():
    streamer = request.args.get("streamer")
    token = get_token()
    url = f"https://api.twitch.tv/helix/streams?user_login={streamer}"
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    r = requests.get(url, headers=headers)
    data = r.json().get("data", [])
    return jsonify({"live": len(data) > 0})
# ======================================
# SERVER START
# ======================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"API HTR démarrée sur le port {port}")
    app.run(host="0.0.0.0", port=port)





