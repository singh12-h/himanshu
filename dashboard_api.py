from flask import Flask, request, render_template_string, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import random
import string
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app)

# SQLite Database Initialization
DATABASE = 'users.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Creating table with price column and adding a column for license status
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        app_id TEXT NOT NULL,
        expiry_time TEXT NOT NULL,   -- Stores expiration date (YYYY-MM-DD HH:MM:SS)
        license_key TEXT NOT NULL,
        price INTEGER DEFAULT 0, -- Price column
        license_status TEXT DEFAULT 'active' -- New Column to track license status
    )''')
    conn.commit()
    conn.close()

init_db()

# Generate a 12-character license key
def generate_license_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

# Emit real-time license update to all connected clients
def emit_license_update(username, new_license_key):
    socketio.emit('license_updated', {
        'username': username,
        'new_license_key': new_license_key
    })

# Home page with user list and regenerate license option
@app.route('/')
def home():
    search_query = request.args.get('search', '')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if search_query:
        c.execute("SELECT * FROM users WHERE username LIKE ? OR license_key LIKE ?", 
                  (f'%{search_query}%', f'%{search_query}%'))
    else:
        c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    return render_template_string('''
    <h1>License Management by Himanshu singh</h1>

    <!-- Search Bar -->
<form id="searchForm" action="/" method="GET">
    <label for="search">Search by Username or License Key:</label>
    <input type="text" id="search" name="search" value="{{ search_query }}" placeholder="Enter username or license key">
    <button type="submit">Search</button>
    <button type="button" id="clearSearch">Clear</button>
</form>

<script>
    document.getElementById("clearSearch").addEventListener("click", function () {
        // Clear input field
        document.getElementById("search").value = "";

        // Reload the current page without search query
        window.location.href = window.location.pathname;
    });
</script>

<h2>Registered Users</h2>

<!-- Table Wrapper -->
<div style="width: 100%; border: 1px solid #ccc; overflow-x: auto;">
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <thead style="position: sticky; top: 0; background: white; z-index: 2;">
            <tr>
                <th style="width: 10%;">ID</th>
                <th style="width: 15%;">Username</th>
                <th style="width: 15%;">App ID</th>
                <th style="width: 30%;">License Key</th>
                <th style="width: 10%;">Price</th>
                <th style="width: 10%;">License Status</th> <!-- License Status Column -->
                <th style="width: 10%;">Actions</th>
                <th style="width: 10%;">Delete</th>
            </tr>
        </thead>
    </table>

    <!-- Scrollable Table Body -->
    <div style="max-height: 250px; overflow-y: auto; width: 100%;">
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <tbody>
                {% for user in users %}
                <tr>
                    <td style="width: 10%;">{{ user[0] }}</td>
                    <td style="width: 15%;">{{ user[1] }}</td>
                    <td style="width: 15%;">{{ user[2] }}</td>
                    <td style="width: 30%;">{{ user[3] }}</td>
                    <td style="width: 10%;">{{ user[4] }}</td>
                    <td style="width: 10%;">{{ user[5] }}</td> <!-- Displaying License Status -->
                    <td style="width: 10%;">
                        <form action="/regenerate_license" method="POST">
                            <input type="hidden" name="username" value="{{ user[1] }}">
                            <input type="hidden" name="app_id" value="{{ user[2] }}">
                            <button type="submit">Regenerate License</button>
                        </form>
                    </td>
                    <td style="width: 10%;">
                        <form action="/delete_user" method="POST">
                            <input type="hidden" name="username" value="{{ user[1] }}">
                            <button type="submit" style="background-color: red; color: white;">Delete User</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

    <div style="display: flex; gap: 30px;">
        <div style="width: 60%;">
            <h2>Generate New User</h2>
            <form action="/generate_license" method="POST">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required><br><br>
                <label for="app_id">App ID:</label>
                <input type="text" id="app_id" name="app_id" required><br><br>
                <button type="submit">Generate License</button>
            </form>
        </div>

        <div style="width: 60%;">
            <h2>Update User Price</h2>
            <form action="/update_user_price" method="POST">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required><br><br>
                <label for="price">New Price:</label>
                <input type="number" id="price" name="price" required><br><br>
                <button type="submit">Update Price</button>
            </form>
        </div>
    </div>
    ''', users=users, search_query=search_query)

# Generate a new license for a new user
@app.route('/generate_license', methods=['POST'])
def generate_license():
    username = request.form['username']
    app_id = request.form['app_id']
    license_key = generate_license_key()
    expiry_time = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, app_id, license_key, expiry_time) VALUES (?, ?, ?, ?)",
              (username, app_id, license_key, expiry_time))
    conn.commit()
    conn.close()

    return redirect(url_for('home'))

# Regenerate a license key for an existing user
@app.route('/regenerate_license', methods=['POST'])
def regenerate_license():
    username = request.form['username']
    app_id = request.form['app_id']

    # Nayi license key generate karte hain
    new_license_key = generate_license_key()

    # Expiry time ko 1 din aage set karte hain
    expiry_time = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    # Database mein update karte hain
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # License key aur expiry time ko update karte hain
    c.execute("UPDATE users SET license_key = ?, expiry_time = ? WHERE username = ? AND app_id = ?",
              (new_license_key, expiry_time, username, app_id))
    conn.commit()
    conn.close()

    # Emit license update to connected clients
    emit_license_update(username, new_license_key)

    return redirect(url_for('home'))

# Update software price for a user
@app.route('/update_user_price', methods=['POST'])
def update_user_price():
    username = request.form['username']
    price = int(request.form['price'])

    # Update the price in the database for the given username
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET price = ? WHERE username = ?", (price, username))
    conn.commit()
    conn.close()

    # After updating the price, redirect back to the home page to reflect the changes
    return redirect(url_for('home'))

# Delete a user
@app.route('/delete_user', methods=['POST'])
def delete_user():
    username = request.form['username']

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    return redirect(url_for('home'))

# License Validation Endpoint
@app.route('/validate_license', methods=['POST'])
def validate_license():
    data = request.get_json()
    username = data.get('username')
    license_key = data.get('license_key')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Remove app_id from the SQL query
    c.execute("SELECT license_key, expiry_time FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user:
        stored_license_key, expiry_time = user
        current_time = datetime.utcnow()

        if stored_license_key == license_key and datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S') > current_time:
            return jsonify({"valid": True, "message": "License is valid"}), 200
        else:
            return jsonify({"valid": False, "message": "License expired"}), 401
    
    return jsonify({"valid": False, "message": "Invalid license"}), 401

@socketio.on('check_license')
def handle_check_license(data):
    username = data['username']
    license_key = data['license_key']

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT license_key FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user:
        current_license_key = user[0]
        if current_license_key != license_key:
            # Notify the client to force logout
            emit('force_logout', {'message': 'Your license key has changed. Please log in again!'}, room=request.sid)
        else:
            emit('license_status', {'valid': True})
    else:
        emit('license_status', {'valid': False, 'message': 'User not found!'})

if __name__ == '__main__':
    socketio.run(app, debug=True)
