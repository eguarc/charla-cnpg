from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        database=os.environ.get('DB_NAME', 'myapp'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres'),
        port=os.environ.get('DB_PORT', '5432')
    )
    return conn

# Initialize database
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('index.html', users=users)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('index.html', users=[])

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    
    if not name or not email:
        flash('Name and email are required!', 'error')
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (name, email) VALUES (%s, %s)', (name, email))
        conn.commit()
        cur.close()
        conn.close()
        flash('User added successfully!', 'success')
    except psycopg2.IntegrityError:
        flash('Email already exists!', 'error')
    except Exception as e:
        flash(f'Error adding user: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)