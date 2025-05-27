#limitations with flask, you cannot render pages multiple times repeatively which blocks the possibility of dynamic tracking

import requests
from flask import Flask, render_template, session, request, redirect
from sqlalchemy.exc import IntegrityError, NoResultFound

from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS

import google.generativeai as genai
from dotenv import load_dotenv

import json
import os
import re

from flask_sqlalchemy import SQLAlchemy

from helpers import login_required


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)
load_dotenv()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

TOKEN = ""

genai.configure(api_key=os.getenv("API_KEY"))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    username = db.Column(db.Text,nullable=False, unique=True)
    hash = db.Column(db.Text, nullable=False)
    token = db.Column(db.Text, nullable=False, unique=True)
    def __repr__(self):
        return f'<User {self.id}>'


@app.route("/")
@login_required
def index():
    return render_template("home.html") 
    
@app.route("/api/logout")
def logout():
    session.clear()
    TOKEN = ""
    return {"Success" : "Successfully Logged out"}

# Saving user Token
@app.route("/api/login", methods=["POST", "GET"])
def login():
    global TOKEN
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")
        try:
            user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
        except NoResultFound:
            return {"error" : "Account Not Found"}
        if not check_password_hash(user.hash, data.get("password")):
            return {"error" : "Incorrect password"}
        session["user_token"] = user.token
        TOKEN = user.token
        print("sucess")
        return {"Success" : "Account Logged in Successfully", "username" : username}
    else:
        session.clear()
        return render_template("login.html")
    
    
@app.route("/api/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        # Valid discord user token format
        regex = re.compile(r"([a-zA-Z0-9]{24})\.([a-zA-Z0-9-]{6})\.([a-zA-Z0-9-_]{38})")
        regex2 = re.compile(r"([a-zA-Z0-9]{26})\.([a-zA-Z0-9-]{6})\.([a-zA-Z0-9-_]{38})")
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        if not username:
            return {"error" : "Please enter a Username"}
        if not password:
            return {"error" : "Please enter a Password"}
        if not (password == data.get("confirm")):
            return {"error" : "Passwords do not match"}
        if not (re.fullmatch(regex, data.get("user_token")) or re.fullmatch(regex2, data.get("user_token"))):
            return {"error" : "Please enter a valid discord token"}
        try:
            user = User(username = username, hash = generate_password_hash(password), token = data.get("user_token"))
            db.session.add(user)
            db.session.commit()
            return {"Success" : "Account created Successfully!", "username" : username}
        except IntegrityError:
            return {"error" : "Username or Token already Exists"}
    else:
        return render_template("register.html")
        
@app.route("/api/monitor", methods=["GET", "POST"])
def monitor():
    if request.method == "POST":                                                                          
        headers = {                                                                                           
        'authorization': TOKEN
        }                      
        request_data = request.get_json()                                                                                  
        channel_id = request_data.get("channel_id")
        try:
            numOfMessages = int(request_data.get("msgCount"))
        except ValueError:
            return {"error" : "Error getting messages (check channel ID)"}
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
            if json.loads(r.text):
            # Saving the last message ID so that the next iteration can query for the next 100 messages
                try:
                    raw_data = json.loads(r.text)
                    lastMsgId = raw_data[-1]["id"]
                    for item in raw_data:
                        if request_data.get("filter") != "":
                            if request_data.get("filter").upper().strip() in item["content"].upper().strip().split():
                                data.append(item)
                        else:
                            data.append(item)
                except KeyError:
                    return {"error" : "Error getting messages"}
            else:
                return {"error" : "No Msgs Found (check channel ID)"}
        return {"data" : data, "channel_id": channel_id}
    else:
        return render_template("monitorinput.html")

# Replying to selected messages
@app.route("/api/message", methods=["POST"])
def message():
    data = request.get_json()
    if data.get("mode") == "manual":
        headers = {
            'authorization': TOKEN
        }
        responses = data.get("reply_array")
        channel = data.get("channel_id")
        reply_text = data.get("reply_text")
        if not channel:
            return {"error" : "Missing channel ID"}
        if not responses:
            return {"error" : "Please select a message to reply to"}
        for item in responses:
            if item != channel and item != reply_text:
                requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers=headers, json={"content": reply_text, "message_reference": {"message_id": f"{item}"}})
        return {"Success" : "Replies sent!"}
    elif data.get("mode") == "ai":
        data = request.get_json()
        # To create a custom prompt insert argument system_instruction="{your prompt}" after "model_name"
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=data.get("prompt"))
        headers = {
            'authorization': TOKEN
        }
        responses = data.get("reply_array")
        channel = data.get("channel_id")
        if not channel or not responses:
            return {"error" : "No Channel or msgs selected"}
        for item in responses:
            if item != channel:
                r = requests.get(f"https://discord.com/api/v10/channels/{channel}/messages?around={item}&limit=1", headers=headers)
                if r:
                    current_msg = json.loads(r.text)
                    requests.post(f"https://discord.com/api/v10/channels/{channel}/messages", headers=headers, json={"content": f"{model.generate_content(f"{current_msg[0]["content"]}").text}", "message_reference": {"message_id": f"{item}"}})
        return {"Success" : "Replies sent!"}
    else:
        return redirect("/monitor")
            
    