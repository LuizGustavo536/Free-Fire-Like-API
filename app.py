from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
import requests
import json
import like_pb2
import like_count_pb2
import uid_generator_pb2
from google.protobuf.message import DecodeError
import base64

# 🔐 KEY SYSTEM
# from auth import check_key
# from db import keys_collection
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)

# ---------------- TOKENS ----------------
def load_tokens():
    try:
        with open("tokens.json", "r") as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Error loading tokens: {e}")
        return None

# ---------------- ENCRYPT ----------------
def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(plaintext, AES.block_size)
        encrypted = cipher.encrypt(padded)
        return binascii.hexlify(encrypted).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting: {e}")
        return None

# ---------------- PROTOBUF ----------------
def create_protobuf_message(user_id, region):
    try:
        msg = like_pb2.like()
        msg.uid = int(user_id)
        msg.region = region
        return msg.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error protobuf: {e}")
        return None

def create_protobuf(uid):
    try:
        msg = uid_generator_pb2.uid_generator()
        msg.saturn_ = int(uid)
        msg.garena = 1
        return msg.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error uid protobuf: {e}")
        return None

def enc(uid):
    proto = create_protobuf(uid)
    if proto is None:
        return None
    return encrypt_message(proto)

# ---------------- REQUEST PLAYER ----------------
def make_request(encrypt, server_name, token):
    try:
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"

        edata = bytes.fromhex(encrypt)

        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB53"
        }

        response = requests.post(url, data=edata, headers=headers, verify=False)

        binary = bytes.fromhex(response.content.hex())

        items = like_count_pb2.Info()
        items.ParseFromString(binary)

        return items

    except Exception as e:
        app.logger.error(f"Erro make_request: {e}")
        return None

# ---------------- SEND LIKE ----------------
async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)

        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB53"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                return await response.text()

    except Exception as e:
        app.logger.error(f"Erro send_request: {e}")
        return None

async def send_multiple_requests(uid, server_name, url):
    try:
        proto = create_protobuf_message(uid, server_name)
        encrypted_uid = encrypt_message(proto)
        tokens = load_tokens()

        if not tokens:
            return None

        total_requests = 220
        concurrency_limit = 10

        semaphore = asyncio.Semaphore(concurrency_limit)

        async def limited_request(token):
            async with semaphore:
                return await send_request(encrypted_uid, token, url)

        tasks = []
        for i in range(total_requests):
            token = tokens[i % len(tokens)]["token"]
            tasks.append(limited_request(token))

        return await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        app.logger.error(f"Erro send_multiple: {e}")
        return None

# ---------------- GERAR KEY ----------------
def generate_key():
    return "FF-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

# ---------------- CREATE KEY ----------------
@app.route('/create-key', methods=['GET'])
def create_key():

    key_type = request.args.get("type", "free").lower()

    if key_type == "free":
        daily_limit = 50
        days = 7
    elif key_type == "vip":
        daily_limit = 200
        days = 30
    elif key_type == "admin":
        daily_limit = 999999999
        days = 3650
    else:
        return jsonify({"error": "Tipo inválido"}), 400

    custom_key = request.args.get("key")
    key = custom_key.upper() if custom_key else generate_key()

    if keys_collection.find_one({"key": key}):
        return jsonify({"error": "Key já existe"}), 400

    data = {
        "key": key,
        "type": key_type,
        "dailyLimit": daily_limit,
        "usedToday": 0,
        "totalUsed": 0,
        "createdAt": datetime.utcnow(),
        "expiresAt": datetime.utcnow() + timedelta(days=days),
        "lastReset": str(datetime.utcnow().date())
    }

    keys_collection.insert_one(data)

    return jsonify({
        "key": key,
        "type": key_type,
        "dailyLimit": daily_limit,
        "validDays": days
    })

# ---------------- INDEX ----------------
@app.route('/')
def index():
    return jsonify({
        "credit": "https://t.me/paglu_dev",
        "status": "API online com sistema de key"
    })

# ---------------- LIKE ----------------
@app.route('/like', methods=['GET'])
def handle_requests():

    # 🔐 KEY CHECK (Desativado para rodar localmente)
    # key_check = check_key()
    # if key_check:
    #     return key_check

    uid = request.args.get("uid")
    if not uid:
        return jsonify({"error": "UID is required"}), 400

    try:
        tokens = load_tokens()
        if not tokens:
            return jsonify({"error": "Tokens inválidos"}), 500

        token = tokens[0]['token']

        # 🔥 DETECTAR REGIÃO AUTOMÁTICO
        server_name = request.args.get("server_name", "").upper()

        if not server_name:
            try:
                payload = token.split('.')[1]
                payload += '=' * (-len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                parsed = json.loads(decoded)
                server_name = parsed.get('lock_region', '').upper()
            except Exception:
                pass

        if not server_name:
            return jsonify({"error": "server_name inválido"}), 400

        encrypted_uid = enc(uid)
        if encrypted_uid is None:
            return jsonify({"error": "Erro ao criptografar UID"}), 500

        # BEFORE
        before = make_request(encrypted_uid, server_name, token)
        if before is None:
            return jsonify({"error": "Erro ao buscar dados do player"}), 500

        data_before = json.loads(MessageToJson(before))
        before_like = int(data_before.get('AccountInfo', {}).get('Likes', 0) or 0)

        # URL LIKE
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/LikeProfile"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/LikeProfile"
        else:
            url = "https://clientbp.ggpolarbear.com/LikeProfile"

        asyncio.run(send_multiple_requests(uid, server_name, url))

        # AFTER
        after = make_request(encrypted_uid, server_name, token)
        if after is None:
            return jsonify({"error": "Erro ao buscar dados após like"}), 500

        data_after = json.loads(MessageToJson(after))
        account_info = data_after.get('AccountInfo', {})

        after_like = int(account_info.get('Likes', 0) or 0)
        player_uid = int(account_info.get('UID', 0) or 0)
        player_name = str(account_info.get('PlayerNickname', ''))

        like_given = after_like - before_like

        return jsonify({
            "credit": "https://t.me/LuizvendasFF",
            "LikesGivenByAPI": like_given,
            "LikesafterCommand": after_like,
            "LikesbeforeCommand": before_like,
            "PlayerNickname": player_name,
            "Region": server_name,
            "UID": player_uid,
            "status": 1 if like_given > 0 else 2
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
