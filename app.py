from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Gmail configuration
GMAIL_USER = 'smetchappy@gmail.com'
GMAIL_PASSWORD = 'ihfoifrlzjvcjea'
GMAIL_SMTP_SERVER = 'smtp.gmail.com'
GMAIL_SMTP_PORT = 587; 

# file upload settings
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = os.path.join(os.path.dirname(__file__), 'blog.db')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            name TEXT NOT NULL,
            description TEXT,
            github_link TEXT,
            completion_time TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # New: AI Projects table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            github_url TEXT,
            description TEXT,
            image_url TEXT,
            progress INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# initialize DB at startup
init_db()

def get_recent_posts(limit=3):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return rows

@app.context_processor
def inject_recent_posts():
    try:
        posts = get_recent_posts(3)
    except Exception:
        posts = []
    return dict(recent_posts=posts)

@app.route('/', methods=['POST'])
def send_contact_email():
    try:
        # Get form data
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Validate required fields
        if not all([name, email, message]):
            flash('Name, email, and message are required', 'error')
            return redirect(url_for('index'))
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER
        msg['Subject'] = f"Website Contact: {subject}"
        
        # Email body
        body = f"""
        New Contact Form Submission:
        
        Name: {name}
        Phone: {phone}
        Email: {email}
        Subject: {subject}
        
        Message:
        {message}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        # Note: smtplib was missing from imports in original file, assuming it's imported or will be added if needed.
        # But for now I'll leave the logic as is, just ensuring indentation is correct.
        import smtplib
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash('Failed to send contact message.', 'error')
        return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

# AI Projects Routes

@app.route('/ai')
def ai_timeline():
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM ai_projects ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('ai_timeline.html', projects=projects)

@app.route('/ai-create', methods=['GET', 'POST'])
def ai_create():
    if request.method == 'POST':
        title = request.form.get('title')
        github_url = request.form.get('github_url')
        description = request.form.get('description')
        image_url = request.form.get('image_url', '').strip()
        try:
            progress = int(request.form.get('progress', 0))
        except ValueError:
            progress = 0
            
        if progress < 0: progress = 0
        if progress > 100: progress = 100
        
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('ai_create'))
            
        conn = get_db_connection()
        conn.execute('INSERT INTO ai_projects (title, github_url, description, image_url, progress, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (title, github_url, description, image_url, progress, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        flash('Project created successfully', 'success')
        return redirect(url_for('ai_timeline'))
        
    return render_template('ai_create.html')

@app.route('/ai-<int:project_id>')
def ai_project_detail(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM ai_projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    if not project:
        return render_template('404.html'), 404
        
    return render_template('ai_project.html', project=project)

@app.route('/ai-manage')
def ai_manage():
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM ai_projects ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('ai_manage.html', projects=projects)

@app.route('/ai-edit/<int:project_id>', methods=['GET', 'POST'])
def ai_edit(project_id):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM ai_projects WHERE id = ?', (project_id,)).fetchone()
    conn.close()
    
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('ai_manage'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        github_url = request.form.get('github_url')
        description = request.form.get('description')
        image_url = request.form.get('image_url', '').strip()
        try:
            progress = int(request.form.get('progress', 0))
        except ValueError:
            progress = 0
            
        if progress < 0: progress = 0
        if progress > 100: progress = 100
        
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('ai_edit', project_id=project_id))
            
        conn = get_db_connection()
        conn.execute('UPDATE ai_projects SET title = ?, github_url = ?, description = ?, image_url = ?, progress = ? WHERE id = ?',
                     (title, github_url, description, image_url, progress, project_id))
        conn.commit()
        conn.close()
        
        flash('Project updated successfully', 'success')
        return redirect(url_for('ai_manage'))
        
    return render_template('ai_edit.html', project=project)

@app.route('/ai-delete/<int:project_id>', methods=['POST'])
def ai_delete(project_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM ai_projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    flash('Project deleted successfully', 'success')
    return redirect(url_for('ai_manage'))

# New: blog upload form + handler
@app.route('/blog-upload', methods=['GET', 'POST'])
def blog_upload():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        github_link = request.form.get('github_link', '').strip()
        completion_time = request.form.get('completion_time', '').strip()  # ISO or any string

        image_url = request.form.get('image_url', '').strip()

        if not name:
            flash('Project name is required.', 'error')
            return redirect(url_for('blog_upload'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO blog_posts (image_url, name, description, github_link, completion_time, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (image_url, name, description, github_link, completion_time, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

        flash('Blog project saved.', 'success')
        return redirect(url_for('blog_posts'))

    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('blog-upload.html', posts=posts)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()

    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('blog_upload'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        github_link = request.form.get('github_link', '').strip()
        completion_time = request.form.get('completion_time', '').strip()

        image_url = request.form.get('image_url', '').strip()

        if not name:
            flash('Project name is required.', 'error')
            return render_template('edit_post.html', post=post)

        conn = get_db_connection()
        conn.execute(
            'UPDATE blog_posts SET name = ?, description = ?, github_link = ?, completion_time = ?, image_url = ? WHERE id = ?',
            (name, description, github_link, completion_time, image_url, post_id)
        )
        conn.commit()
        conn.close()

        flash('Post updated successfully.', 'success')
        return redirect(url_for('blog_upload'))

    return render_template('edit_post.html', post=post)

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM blog_posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('blog_upload'))

# New: list saved blog posts
@app.route('/blog-posts')
def blog_posts():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('blog-posts.html', posts=rows)

@app.route('/blog/<int:post_id>')
def blog_details(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    if not post:
        flash('Post not found', 'error')
        return redirect(url_for('index'))
    # sqlite3.Row is mapping-like; convert to dict for template if needed
    post_dict = dict(post)
    return render_template('blog-details.html', post=post_dict)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)