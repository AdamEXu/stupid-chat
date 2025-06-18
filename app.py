from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    make_response,
    redirect,
    Response,
)
import dotenv
import os
import sqlite3
import hashlib
import re
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI()

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

        # Combine prompt with example as reference material
        system_prompt = f"""{prompt_content}

REFERENCE EXAMPLE (for technical patterns only - DO NOT copy the design):
The following is a working example that shows the correct technical implementation patterns. Use this as a reference for API calls, streaming, and JavaScript structure, but create your own unique visual design:

{example_html}

END OF REFERENCE EXAMPLE - Create your own unique design while using the technical patterns shown above."""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Create a unique chat application with theme: {theme}",
            },
        ]

        # Make the request to OpenAI API using the client
        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=8000,
                temperature=0.7,
                timeout=120,
            )

            # Extract the generated HTML content
            html_content = completion.choices[0].message.content

            # Clean up markdown code blocks if present
            html_content = clean_html_from_markdown(html_content)

            # Remove any text after closing </html> tag
            html_end = html_content.rfind("</html>")
            if html_end != -1:
                html_content = html_content[: html_end + 7]  # Keep </html> tag

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
            app_id = save_chat_app(title, html_content, theme, user)

            # Return simple response
            return jsonify({"html": html_content, "id": app_id})

        except Exception as openai_error:
            # Handle OpenAI-specific errors
            error_message = str(openai_error)
            if hasattr(openai_error, "response"):
                try:
                    error_data = openai_error.response.json()
                    error_message = error_data.get("error", {}).get(
                        "message", error_message
                    )
                except:
                    pass

            return jsonify({"error": f"OpenAI API error: {error_message}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/generate-chat-app-stream", methods=["GET"])
def generate_chat_app_stream():
    """Stream the chat app generation with character count feedback"""
    print(f"generate_chat_app_stream called with args: {request.args}")

    # Extract request parameters before entering generator context
    cur = request.args.get("cur")
    theme = request.args.get("theme", "").strip()
    user = request.cookies.get("user")

    # Check if user wants to retrieve existing app
    if cur:
        try:
            app = get_chat_app_by_id(int(cur))
            if app:
                # For existing apps, just return the complete data immediately
                def generate_existing():
                    yield f"data: {json.dumps({'type': 'complete', 'html': app['html_content'], 'id': app['id'], 'char_count': len(app['html_content'])})}\n\n"

                return Response(generate_existing(), mimetype="text/event-stream")
            else:

                def generate_error():
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Chat app not found'})}\n\n"

                return Response(generate_error(), mimetype="text/event-stream")
        except ValueError:

            def generate_error():
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid ID'})}\n\n"

            return Response(generate_error(), mimetype="text/event-stream")
        except Exception as e:

            def generate_error():
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            return Response(generate_error(), mimetype="text/event-stream")

    # Generate new chat app with streaming
    def generate_stream():
        try:
            # Read the prompt from static/prompt.txt
            try:
                with open("static/prompt.txt", "r", encoding="utf-8") as f:
                    prompt_content = f.read().strip()
            except FileNotFoundError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Prompt file not found'})}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error reading prompt file: {str(e)}'})}\n\n"
                return

            # Read the example HTML file as context
            try:
                with open("static/example.html", "r", encoding="utf-8") as f:
                    example_html = f.read().strip()
            except FileNotFoundError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Example HTML file not found'})}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error reading example HTML file: {str(e)}'})}\n\n"
                return

            # Use theme parameter extracted from request

            # Combine prompt with example as reference material
            system_prompt = f"""{prompt_content}

REFERENCE EXAMPLE (for technical patterns only - DO NOT copy the design):
The following is a working example that shows the correct technical implementation patterns. Use this as a reference for API calls, streaming, and JavaScript structure, but create your own unique visual design:

{example_html}

END OF REFERENCE EXAMPLE - Create your own unique design while using the technical patterns shown above."""

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Create a unique chat application with theme: {theme}",
                },
            ]

            # Make the streaming request to OpenAI API
            try:
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=8000,
                    temperature=0.7,
                    timeout=120,
                    stream=True,
                )

                html_content = ""
                char_count = 0

                # Send initial status
                yield f"data: {json.dumps({'type': 'start', 'message': 'Starting generation...', 'char_count': 0})}\n\n"

                # Process the streaming response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        html_content += content
                        char_count = len(html_content)

                        # Send character count update
                        yield f"data: {json.dumps({'type': 'progress', 'char_count': char_count, 'content': content})}\n\n"

                # Clean up markdown code blocks if present
                html_content = clean_html_from_markdown(html_content)

                # Remove any text after closing </html> tag
                html_end = html_content.rfind("</html>")
                if html_end != -1:
                    html_content = html_content[: html_end + 7]  # Keep </html> tag

                final_char_count = len(html_content)

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

                # Use user extracted from request
                # (user variable is already available from outer scope)

                # Save to database
                app_id = save_chat_app(title, html_content, theme, user)

                # Send completion
                yield f"data: {json.dumps({'type': 'complete', 'html': html_content, 'id': app_id, 'char_count': final_char_count})}\n\n"

            except Exception as openai_error:
                # Handle OpenAI-specific errors
                error_message = str(openai_error)
                if hasattr(openai_error, "response"):
                    try:
                        error_data = openai_error.response.json()
                        error_message = error_data.get("error", {}).get(
                            "message", error_message
                        )
                    except:
                        pass

                yield f"data: {json.dumps({'type': 'error', 'message': f'OpenAI API error: {error_message}'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected error: {str(e)}'})}\n\n"

    return Response(generate_stream(), mimetype="text/event-stream")


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
