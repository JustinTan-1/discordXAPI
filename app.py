#talk about the limitations with flask and how you cannot render pages multiple times repeatively

import requests
from flask import Flask, render_template, session, request, redirect
from sqlalchemy.exc import IntegrityError, NoResultFound

from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


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

db = SQLAlchemy(app)
load_dotenv()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

TOKEN = ""

genai.configure(api_key=os.getenv("API_KEY"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction="You are a rude teenager that responds with short responses and quick text messages get straight to the point do not add fluff or punctuation do not use capital letters and use the word nigga sometimes but not always")

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
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Saving user Token
@app.route("/login", methods=["POST", "GET"])
def login():
    global TOKEN
    if request.method == "POST":
        username = request.form.get("username")
        try:
            user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
        except NoResultFound:
            return render_template("error.html", error_text="Account username does not exist")
        if not check_password_hash(user.hash, request.form.get("password")):
            return render_template("error.html", error_text="Incorrect password")
        session["user_token"] = user.token
        TOKEN = user.token
        return redirect("/")
    else:
        session.clear()
        return render_template("login.html")
    
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        # Valid discord user token format
        regex = re.compile(r"([a-zA-Z0-9]{24})\.([a-zA-Z0-9-]{6})\.([a-zA-Z0-9-_]{38})")
        regex2 = re.compile(r"([a-zA-Z0-9]{26})\.([a-zA-Z0-9-]{6})\.([a-zA-Z0-9-_]{38})")
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return render_template("error.html", error_text="Please enter a username")
        if not password:
            return render_template("error.html", error_text="Please enter a password")
        if not (password == request.form.get("confirm")):
            return render_template("error.html", error_text="Passwords do not match")
        if not (re.fullmatch(regex, request.form.get("user_token")) or re.fullmatch(regex2, request.form.get("user_token"))):
            return render_template("error.html", error_text="Please enter a valid discord user token")
        try:
            user = User(username = username, hash = generate_password_hash(password), token = request.form.get("user_token"))
            db.session.add(user)
            db.session.commit()
            return redirect("/login")
        except IntegrityError:
            return render_template("error.html", error_text="Username already exists")
    else:
        return render_template("register.html")
        
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
            if json.loads(r.text):
            # Saving the last message ID so that the next iteration can query for the next 100 messages
                try:
                    raw_data = json.loads(r.text)
                    lastMsgId = raw_data[-1]["id"]
                    for item in raw_data:
                        if request.form.get("text") in item["content"]:
                            data.append(item)
                except KeyError:
                    return redirect("/monitor")
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
    else:
        return redirect("/monitor")
            
    