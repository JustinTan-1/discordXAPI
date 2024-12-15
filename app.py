#talk about the limitations with flask and how you cannot render pages multiple times repeatively

import requests
from flask import Flask, render_template, session, request, redirect
import json
import google.generativeai as genai
from dotenv import load_dotenv
import os

from helpers import login_required


from flask_session import Session

app = Flask(__name__)
load_dotenv()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

TOKEN = ""

genai.configure(api_key=os.getenv("API_KEY"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction="You are a rude teenager that responds with short responses and quick text messages get straight to the point do not add fluff or punctuation do not use capital letters and use the word nigga sometimes but not always")

@app.route("/")
@login_required
def index():
    return render_template("home.html") 
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Saving user Token
@app.route("/login", methods=["POST", "GET"])
def login():
    global TOKEN
    if request.method == "POST":
        if not request.form.get("user_token"):
            return redirect("/login")
        session["user_token"] = request.form.get("user_token")
        TOKEN = request.form.get("user_token")
        return redirect("/")
    else:
        session.clear()
        return render_template("login.html")
    

@app.route("/monitor", methods=["GET", "POST"])
@login_required
def monitor():
    if request.method == "POST":                                                                          
        headers = {                                                                                           
        'authorization': TOKEN
        }                                                                                                        
        channel_id = request.form.get("channel_id")
        try:
            numOfMessages = int(request.form.get("msgCount"))
        except ValueError:
            return redirect("/monitor")
        data = []
        firstTime = True
        for i in range (0, numOfMessages):
            # If it is the first time, only query the first 100 msgs
            if firstTime:
                r = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100", headers=headers)
                firstTime = False
            # query for the next 100 messages
            else:
                r = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100&before={lastMsgId}", headers=headers)
            if r:
            # Saving the last message ID so that the next iteration can query for the next 100 messages
                raw_data = json.loads(r.text)
                lastMsgId = raw_data[-1]["id"]
                for item in raw_data:
                    if request.form.get("text") in item["content"]:
                        data.append(item)
            else:
                return redirect("/monitor")
        return render_template("monitor.html", data=data, channel_id=channel_id)  
    else:
        return render_template("monitorinput.html")

# Replying to selected messages
@app.route("/message", methods=["POST"])
@login_required
def message():
    if request.form.get("mode") == "manual":
        headers = {
            'authorization': TOKEN
        }
        responses = request.form
        channel = request.form.get("channel_id")
        reply_text = request.form.get("reply_text")
        if not channel or not responses:
            return redirect("/monitor")
        for item in responses:
            if item != channel and item != reply_text:
                requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers=headers, json={"content": reply_text, "message_reference": {"message_id": f"{item}"}})
        return redirect("/monitor")
    elif request.form.get("mode") == "ai":
        global model
        headers = {
            'authorization': TOKEN
        }
        responses = request.form
        channel = request.form.get("channel_id")
        if not channel or not responses:
            return redirect("/monitor")
        for item in responses:
            if item != channel:
                r = requests.get(f"https://discord.com/api/v10/channels/{channel}/messages?around={item}&limit=1", headers=headers)
                if r:
                    current_msg = json.loads(r.text)
                    requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers=headers, json={"content": f"{model.generate_content(f"{current_msg[0]["content"]}").text}", "message_reference": {"message_id": f"{item}"}})
        return redirect("/monitor")
            
    