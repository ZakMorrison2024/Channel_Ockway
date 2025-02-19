from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from PIL import Image
from waitress import serve

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bulletin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['UPLOAD_FOLDER_ITEMS'] = 'static/uploads/items'

os.makedirs(app.config['UPLOAD_FOLDER_ITEMS'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    no = db.Column(db.Integer, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)


@app.route('/')
def index():
    posts = Post.query.all()
    categories = {post.category for post in posts} 
    return render_template('index.html', posts=posts, categories=categories)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/rules')
def rules():
    return render_template('rules.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
      
    flash('Invalid username or password.', 'error')
    return redirect(url_for('index'))    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        no = request.form['no']
        new_user = User(username=username, password=password, no=no)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Access denied. Admins only.", "error")
        return redirect(url_for('index'))
    users = User.query.all()
    posts = Post.query.all()
    return render_template('admin.html', users=users, posts=posts)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    print(f"Received request method: {request.method}")  # Debugging line
    if not session.get('is_admin'):
        flash("Access denied.", "error")
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("User logged out successfully.", "success")
    return redirect(url_for('index'))


@app.route('/create', methods=['GET', 'POST'])
def create():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        picture = request.files.get('picture')
        category = request.form['category']
        if picture and allowed_file(picture.filename):
            try:
                img = Image.open(picture)
                img.verify()
                filename = secure_filename(picture.filename)
                picture_path = os.path.join(app.config['UPLOAD_FOLDER_ITEMS'], filename)
                picture.seek(0)
                picture.save(picture_path)
                image_path = f"items/{filename}"
            except Exception as e:
                flash(f"Picture Upload Failed: {str(e)}.", "error")
                image_path = f"static/placeholder_0.jpg"
        else:
            image_path = f"static/placeholder_0.jpg"
            flash("Error: Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.", "error")
        new_post = Post(title=title, content=content,category=category, author=session['user'], image_path=image_path)
        flash("Post uploaded successfully!", "success")
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id) 
    if session.get('is_admin') or post.author == session.get('user'):
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    else:
        flash('You are not authorized to delete this post.', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
     with app.app_context():
        db.create_all() 
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(username="admin", password=generate_password_hash("Admin@OCKWAY2025"), is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists. Skipping creation.")

     serve(app, host="0.0.0.0", port=5000)
