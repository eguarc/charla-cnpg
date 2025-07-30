from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'postgres'),
    'database': os.environ.get('DB_NAME', 'app_db'),
    'user': os.environ.get('DB_USER', 'app_user'),
    'password': os.environ.get('DB_PASSWORD', 'app_password'),
    'port': os.environ.get('DB_PORT', '5432')
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        with conn.cursor() as cur:
            # Create tasks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create trigger for updated_at
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            cur.execute("""
                DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
                CREATE TRIGGER update_tasks_updated_at
                    BEFORE UPDATE ON tasks
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)
            
        conn.commit()
        logger.info("Database initialized successfully")
        return True
    except psycopg2.Error as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

@app.route('/')
def index():
    """Main dashboard"""
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return render_template('error.html', message='Cannot connect to database')
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM tasks 
                ORDER BY 
                    CASE WHEN status = 'pending' THEN 1
                         WHEN status = 'in_progress' THEN 2
                         ELSE 3 END,
                    created_at DESC
            """)
            tasks = cur.fetchall()
            
        # Get statistics
        with conn.cursor() as cur:
            cur.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
            stats = dict(cur.fetchall())
            
    except psycopg2.Error as e:
        logger.error(f"Query error: {e}")
        flash('Error loading tasks', 'error')
        tasks = []
        stats = {}
    finally:
        conn.close()
    
    return render_template('index.html', tasks=tasks, stats=stats)

@app.route('/add', methods=['GET', 'POST'])
def add_task():
    """Add new task"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('Title is required', 'error')
            return render_template('add_task.html')
        
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'error')
            return render_template('add_task.html')
        
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tasks (title, description) VALUES (%s, %s)",
                    (title, description)
                )
            conn.commit()
            flash('Task added successfully!', 'success')
            return redirect(url_for('index'))
        except psycopg2.Error as e:
            logger.error(f"Insert error: {e}")
            flash('Error adding task', 'error')
            conn.rollback()
        finally:
            conn.close()
    
    return render_template('add_task.html')

@app.route('/update/<int:task_id>', methods=['POST'])
def update_task_status(task_id):
    """Update task status via AJAX"""
    new_status = request.json.get('status')
    
    if new_status not in ['pending', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET status = %s WHERE id = %s",
                (new_status, task_id)
            )
        conn.commit()
        return jsonify({'success': True, 'status': new_status})
    except psycopg2.Error as e:
        logger.error(f"Update error: {e}")
        conn.rollback()
        return jsonify({'error': 'Database error'}), 500
    finally:
        conn.close()

@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete task"""
    
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        flash('Task deleted successfully!', 'success')
    except psycopg2.Error as e:
        logger.error(f"Delete error: {e}")
        flash('Error deleting task', 'error')
        conn.rollback()
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except:
        return jsonify({'status': 'unhealthy', 'database': 'error'}), 503

if __name__ == '__main__':
    # Initialize database on startup
    if init_db():
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        logger.error("Failed to initialize database. Exiting.")
        exit(1)
