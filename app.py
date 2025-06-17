from flask import (
    Flask,
    request,
    jsonify,
    Response,
    render_template,
    render_template,
    make_response,
    redirect,
)
import dotenv
import os
import requests
import json
import sqlite3
import hashlib
import re
from datetime import datetime

dotenv.load_dotenv()

app = Flask(__name__)


# Database setup
def init_db():
    """Initialize the SQLite database with the chat_apps table"""
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            html_content TEXT NOT NULL,
            prompt_used TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content_hash TEXT UNIQUE NOT NULL,
            user TEXT
        )
    """
    )

    conn.commit()
    conn.close()


def save_chat_app(title, html_content, prompt_used, user=None):
    """Save a generated chat app to the database"""
    # Create a hash of the content to avoid duplicates
    content_hash = hashlib.md5(html_content.encode()).hexdigest()

    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO chat_apps (title, html_content, prompt_used, content_hash, user)
            VALUES (?, ?, ?, ?, ?)
        """,
            (title, html_content, prompt_used, content_hash, user),
        )

        app_id = cursor.lastrowid
        conn.commit()
        return app_id
    except sqlite3.IntegrityError:
        # App with this content already exists
        cursor.execute(
            "SELECT id FROM chat_apps WHERE content_hash = ?", (content_hash,)
        )
        existing_id = cursor.fetchone()[0]
        return existing_id
    finally:
        conn.close()


def get_all_chat_apps():
    """Get all saved chat apps with basic info"""
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at,
               SUBSTR(html_content, 1, 200) as preview
        FROM chat_apps
        ORDER BY created_at DESC
    """
    )

    apps = cursor.fetchall()
    conn.close()

    return [
        {
            "id": app[0],
            "title": app[1],
            "created_at": app[2],
            "preview": app[3] + "..." if len(app[3]) >= 200 else app[3],
        }
        for app in apps
    ]


def get_chat_apps_by_user(user):
    """Get all saved chat apps for a specific user"""
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at,
               SUBSTR(html_content, 1, 200) as preview
        FROM chat_apps
        WHERE user = ?
        ORDER BY created_at DESC
    """,
        (user,),
    )

    apps = cursor.fetchall()
    conn.close()

    return [
        {
            "id": app[0],
            "title": app[1],
            "created_at": app[2],
            "preview": app[3] + "..." if len(app[3]) >= 200 else app[3],
        }
        for app in apps
    ]


def get_chat_app_by_id(app_id):
    """Get a specific chat app by ID"""
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, html_content, prompt_used, created_at
        FROM chat_apps
        WHERE id = ?
    """,
        (app_id,),
    )

    app = cursor.fetchone()
    conn.close()

    if app:
        return {
            "id": app[0],
            "title": app[1],
            "html_content": app[2],
            "prompt_used": app[3],
            "created_at": app[4],
        }
    return None


# Initialize database on startup
init_db()


def clean_html_from_markdown(content):
    """Remove markdown code block formatting from HTML content"""
    # Remove ```html and ``` markers
    content = re.sub(r"^```html\s*\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^```\s*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n```\s*$", "", content)
    content = re.sub(r"^```\s*\n", "", content, flags=re.MULTILINE)

    # Remove any remaining ``` at start or end
    content = content.strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    return content.strip()


@app.route("/")
def index():
    user = request.cookies.get("user")
    first = user.split("|")[0] if user else None
    last = user.split("|")[1] if user else None
    password = user.split("|")[2] if user else None

    # Get user-specific chat apps if user is logged in
    clones = []
    if user:
        clones = get_chat_apps_by_user(user)

    return render_template(
        "index.html",
        user=user,
        first=first,
        last=last,
        password=password,
        clones=clones,
    )


@app.route("/generate-chat-app", methods=["GET"])
def generate_chat_app():
    print(f"generate_chat_app called with args: {request.args}")
    # Check if user wants to retrieve existing app
    cur = request.args.get("cur")
    if cur:
        try:
            app = get_chat_app_by_id(int(cur))
            if app:
                return jsonify({"html": app["html_content"], "id": app["id"]})
            else:
                return jsonify({"error": "Chat app not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid ID"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Generate new chat app
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        # print(f"API Key present: {bool(api_key)}")
        if not api_key:
            return jsonify({"error": "OpenAI API key not configured"}), 500

        # Read the prompt from static/prompt.txt
        try:
            with open("static/prompt.txt", "r", encoding="utf-8") as f:
                prompt_content = f.read().strip()
        except FileNotFoundError:
            return jsonify({"error": "Prompt file not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Error reading prompt file: {str(e)}"}), 500

        # Read the example HTML file as context
        try:
            with open("static/example.html", "r", encoding="utf-8") as f:
                example_html = f.read().strip()
        except FileNotFoundError:
            return jsonify({"error": "Example HTML file not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Error reading example HTML file: {str(e)}"}), 500

        # Get theme parameter if provided
        theme = request.args.get("theme", "").strip()

        # Combine prompt with example context
        full_prompt = f"""{prompt_content}

Here's an example of a well-structured chat application for reference:

```html
{example_html}
```

Use this example as inspiration for structure, styling, and functionality, but create a unique variation with different visual design, colors, layout, or features. Make sure your generated HTML is complete and self-contained."""

        # Append theme if provided
        if theme:
            full_prompt += (
                f"\n\nAdditional theme/style requirement from the user: {theme}"
            )

        # Set up headers for OpenAI API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Prepare the request payload (non-streaming)
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 4000,
            "temperature": 0.7,
        }

        # Make the request to OpenAI API
        openai_url = "https://api.openai.com/v1/chat/completions"
        # print(f"Making request to OpenAI with payload: {payload}")
        response = requests.post(openai_url, headers=headers, json=payload, timeout=120)
        # print(f"OpenAI response status: {response.status_code}")
        # print(f"OpenAI response: {response.text[:500]}")

        if response.status_code == 200:
            response_data = response.json()

            # Extract the generated HTML content
            if "choices" in response_data and len(response_data["choices"]) > 0:
                html_content = response_data["choices"][0]["message"]["content"]

                # Clean up markdown code blocks if present
                html_content = clean_html_from_markdown(html_content)

                # Generate a title from the first few words of the HTML or use a default
                title = "Generated Chat App"
                try:
                    # Try to extract title from HTML title tag
                    title_match = re.search(
                        r"<title>(.*?)</title>", html_content, re.IGNORECASE
                    )
                    if title_match:
                        title = title_match.group(1).strip()
                    else:
                        # Use timestamp as fallback
                        title = f"Chat App {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                except:
                    title = f"Chat App {datetime.now().strftime('%Y-%m-%d %H:%M')}"

                # Get user from cookies
                user = request.cookies.get("user")

                # Save to database
                app_id = save_chat_app(title, html_content, full_prompt, user)

                # Return simple response
                return jsonify({"html": html_content, "id": app_id})
        else:
            # Return the actual OpenAI error
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get(
                    "message", "Unknown OpenAI error"
                )
                return (
                    jsonify({"error": f"OpenAI API error: {error_msg}"}),
                    response.status_code,
                )
            except:
                return (
                    jsonify(
                        {"error": f"OpenAI API error (status {response.status_code})"}
                    ),
                    response.status_code,
                )

        return jsonify({"error": "Failed to generate chat app"}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request to OpenAI failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        # just store it in a cookie
        first = request.form.get("first")
        last = request.form.get("last")
        password = request.form.get("password")
        cookie = f"{first}|{last}|{password}"
        response = make_response(redirect("/"))
        response.set_cookie("user", cookie)
        return response


@app.route("/logout")
def logout():
    response = make_response(redirect("/"))
    response.set_cookie("user", "")
    return response


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=os.environ.get("PORT", 3545),
        debug=False if os.environ.get("PROD") else True,
    )
