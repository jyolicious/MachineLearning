from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from collections import Counter, defaultdict
import re
import emoji
from datetime import datetime
from wordcloud import STOPWORDS


app = FastAPI(title="WhatsApp Chat Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pattern = r"^(\d+/\d+/\d+),\s(\d+:\d+)\s-\s([^:]+):\s(.+)"

def parse_chat(text):
    messages = []
    for line in text.split("\n"):
        match = re.match(pattern, line)
        if match:
            date, time, user, msg = match.groups()
            dt = datetime.strptime(date + " " + time, "%d/%m/%y %H:%M")
            messages.append({
                "user": user,
                "message": msg,
                "date": dt.date().isoformat(),
                "hour": dt.hour
            })
    return messages

@app.post("/upload")
async def upload_chat(file: UploadFile = File(...)):
    text = (await file.read()).decode("utf-8", errors="ignore")
    data = parse_chat(text)

    user_count = Counter()
    daily_count = Counter()
    hourly_count = Counter()
    emoji_count = Counter()
    message_length = defaultdict(list)
    media_count = Counter()

    for d in data:
        user = d["user"]
        msg = d["message"]

        user_count[user] += 1
        daily_count[d["date"]] += 1
        hourly_count[d["hour"]] += 1
        message_length[user].append(len(msg))

        emojis = [c for c in msg if c in emoji.EMOJI_DATA]
        emoji_count[user] += len(emojis)

        if "<media omitted>" in msg.lower():
            media_count[user] += 1

    avg_msg_length = {
        u: sum(l) // len(l) for u, l in message_length.items()
    }
    word_freq = generate_word_freq(data)

    return {
        "total_messages": len(data),
        "messages_per_user": dict(user_count),
        "messages_per_day": dict(daily_count),
        "messages_per_hour": dict(hourly_count),
        "emoji_count_per_user": dict(emoji_count),
        "avg_message_length": avg_msg_length,
        "media_messages": dict(media_count),
        "word_cloud": word_freq
    }
def generate_word_freq(data):
    stopwords = set(STOPWORDS)
    words = []

    for d in data:
        msg = d["message"].lower()

        # ignore media & group system messages
        if "<media omitted>" in msg:
            continue
        if "added" in msg or "left" in msg or "joined" in msg:
            continue

        for word in msg.split():
            if word.isalpha() and word not in stopwords:
                words.append(word)

    return dict(Counter(words))

