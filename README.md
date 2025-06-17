# Generate T3 Chat Clone

Click the button on the website with a design Theo will surely love and it'll give you a T3 Chat clone. Not a good one, but a clone nonetheless. [t3.chat](https://www.youtube.com/watch?v=dQw4w9WgXcQ) is a ai chat website, which I assume means that it's an ai generated website where ai can chat with you...

## Features (ai generated)

### 🤖 AI-Powered Chat App Generation

-   **One-Click Generation**: Generate complete, functional chat applications with a single button click
-   **Custom Theming**: Personalize your chat app by specifying themes or styles in the input field
-   **OpenAI GPT-4o Integration**: Powered by OpenAI's latest model for high-quality HTML generation
-   **Self-Contained Output**: Generated apps are complete HTML files with inline CSS and JavaScript - no external dependencies

### 💬 Generated Chat Applications Include

-   **OpenRouter API Integration**: Connect to 200+ AI models through OpenRouter
-   **Real-time Streaming**: Live token-by-token response streaming for natural conversation flow
-   **Model Selection**: Choose from multiple AI models including Llama 3.3 70B Instruct (free)
-   **Conversation Management**: In-memory chat history with clear conversation functionality
-   **Responsive Design**: Modern, mobile-friendly interfaces that adapt to different screen sizes
-   **Error Handling**: Graceful handling of API errors and network issues

### 🗄️ Persistence & History

-   **SQLite Database**: All generated chat apps are automatically saved to a local database
-   **Unique Content Detection**: Prevents duplicate apps using MD5 content hashing
-   **Retrieval System**: Access any previously generated app using `/?cur=ID` URL format
-   **User-Specific History**: Logged-in users can view and access their personal chat app collection
-   **Automatic Timestamping**: Track when each chat app was created

### 🔐 Authentication System

-   **Cookie-Based Sessions**: Simple authentication using browser cookies
-   **User-Specific Content**: Personal chat app libraries for logged-in users
-   **Secure Password Validation**: Pre-approved password system for maximum security
-   **Intelligent Name Suggestions**: Our system intelligently suggests potential usernames
-   **Easy Logout**: Clear browser data to logout

### 🎨 User Experience

-   **URL Management**: Automatic URL updates with app IDs for easy sharing and bookmarking
-   **Loading States**: Clear feedback during the AI generation process
-   **Error Messages**: Helpful error messages when things go wrong (which they will)
-   **Responsive Interface**: Works on desktop and mobile devices

### 🛠️ Technical Features

-   **Flask Backend**: Python Flask application with clean API endpoints
-   **Static File Serving**: Efficient serving of CSS, JavaScript, and HTML assets
-   **Environment Configuration**: Configurable for development and production environments
-   **Modular Architecture**: Clean separation of concerns with dedicated functions for each feature
-   **Content Sanitization**: Automatic cleanup of markdown formatting from AI responses

### 🎯 API Endpoints

-   `GET /` - Main application interface with user dashboard
-   `GET /generate-chat-app` - Generate new chat apps or retrieve existing ones
-   `GET|POST /login` - User authentication
-   `GET /logout` - Session termination

### 🔧 Developer Features

-   **Open Source**: Full source code available on GitHub
-   **Easy Setup**: Simple installation with pip and virtual environments
-   **Configurable**: Environment variables for API keys and settings
-   **Extensible**: Clean codebase for easy feature additions and modifications

## Running it locally

Idk why you'd ever want to run this stupid code locally but it's pretty simple

I use a Mac so instructions are for Mac. If you don't use a Mac go ask chatgpt to explain how to make it work ig.

First clone the repo

```
git clone https://github.com/AdamEXu/stupid-chat.git
cd stupid-chat
```

Then, you will create a Python virtual enviroment (please do this, if you don't you are a psycopath)

```
python3 -m venv env
source env/bin/activate
```

Now install dependencies

```
pip install -r requirements.txt
```

And run

```
python app.py
```

Congrats, you now have a T3 Chat clone generator.
