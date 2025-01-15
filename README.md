# Discord Channel Monitor
#### Description:
A Discord Channel monitor that reads messages from discord channels and displays them. Users can filter messages by text and select messages to reply to through the UI with a single reply or generate replies through Google Gemini AI. 

## Specifications
This application is created using flask. HTML/CSS templates are generated and rendered using Jinja syntax. Required dependancies: Flask, SQLAlchemy, GoogleGenAI, .env, 

## Installation
To clone and run this application, you need Git and the required dependancies. You will also need to create a file in the project directory called "database.db".

You will also need to create a .env file with a GoogleGemini API key
```console
# Your API key here
API_KEY = ""
```

```console
$ git clone https://github.com/JustinTan-1/discordtool.git

$ cd discordtool

# Run after all dependancies have been installed and database has been created
$ flask run
```

## How to get User Token on Discord

**WARNING!** Do not share this token with anyone, as it will provide full access to your Discord account.

Head to https://discord.com and login into your discord account. Once you have logged in, inspect the page with CTRL+SHIFT+I and head over to the network page. In the filter box, type in "/api" and click on any of the options. Search for the "Authorization" section and copy the string of characters beside Token.

## Login/Register
On the home page, the user is prompted for login or registration through a discord user token. Login details and user tokens are stored on an SQLite database. Without a user token being stored in a user session, the user is unable to access the discord monitoring features.

## Discord API Notes
User enters a channel ID from the text input box. The application queries the discord API via the following get template:

https://discord.com/api/v10/channels/{channel_id}/messages?limit=100, headers=headers

It is important to include a header argument with headers including "authorization": user_token, where the user_token is retrived at login, and where channel_id is retrieved from the user through a POST request. The request WILL NOT work without the user token. The result is parsed to JSON, which allows for easy access of message properties. Each message is then iterated through with the message, timestamp, and sender username displayed into the viewport. Optionally, the user can type in text that they would like to see in the results. In this case, each object return in the raw data is compared to the text that the user imputted and only the messages that include the user's specified text are displayed on the screen. If the request fails, the user is redirected back to the monitoring page.

## Message Reply
Once the messages are displayed on screen, the user can check a checkbox beside which toggles an input value in a form. Once the form is submitted by pressing "Reply", all the message ID's retrived through the GET request are passed as inputs in the form as well as the intended reply and the channel ID. All this information is sent through new API POST request that initiates a reply to the specified messages, which can be seen through the following argument template:

https://discord.com/api/v10/channels/{channel}/messages", headers=headers, json={"content": reply_text, "message_reference": {"message_id": f"{item}"}}

Once again, it is important to include user token in headers. Additionally, a json argument is required for this specific POST request that includes the type of message that will be posted and the content of the message. In this case, the Discord API uses "message_referece" to indicate a message reply. Once all replys are successfully sent, the user is redirected back to the monitor page.


## Future Improvements
- Transistion PostgreSQL if application will be used extensively
- Allow the user to create unique replies for each selected message
- Allow the user to specify date and time and/or specific usernames
- Transitioning to a different framework such as React could allow for dynamic re-rendering of the pages and a solution to consistently listen for new messages in a channel
