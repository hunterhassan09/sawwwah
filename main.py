# -*- coding: utf-8 -*-
"""
Main Flask application file for the University Search Website.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__))) # DON'T CHANGE THIS !!!

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

from src.models import db, University, User
from src.forms import LoginForm, RegistrationForm

# Create Flask app instance
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = os.urandom(24)

# Configure database - Using SQLite for simplicity in development
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "../university_data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page" # Redirect to login page if user tries to access protected page
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables if they don't exist
# Moved seeding to a separate script (seed_db.py)
# with app.app_context():
#     db.create_all()

# --- Routes --- #

@app.route("/")
def index():
    """Renders the home page."""
    return render_template("index.html", title="Home")

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method="pbkdf2:sha256")
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! You are now able to log in", "success")
        return redirect(url_for("login_page"))
    return render_template("register.html", title="Register", form=form)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            flash("Login Successful!", "success")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        else:
            flash("Login Unsuccessful. Please check email and password", "danger")
    return render_template("login.html", title="Login", form=form)

@app.route("/logout")
@login_required
def logout_page():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/favorites")
@login_required
def favorites_page():
    user_favorites = current_user.favorites # Access the favorites relationship
    return render_template("favorites.html", title="My Favorites", favorites=user_favorites)

@app.route("/region/<region_name>")
def region_page(region_name):
    # Fetch universities by region
    universities = University.query.filter(University.region.ilike(f"%{region_name}%")).order_by(University.name).all()
    return render_template("region.html", title=f"{region_name} Universities", region_name=region_name, universities=universities)

@app.route("/university/<int:university_id>")
def university_page(university_id):
    university = University.query.get_or_404(university_id)
    return render_template("university_detail.html", title=university.name, university=university)

@app.route("/search")
def search_page():
    query = request.args.get("query", "")
    region = request.args.get("region", "")
    country = request.args.get("country", "")
    city = request.args.get("city", "")
    min_rank_str = request.args.get("min_rank", "")
    max_acceptance_str = request.args.get("max_acceptance", "")
    uni_type = request.args.get("type", "")

    results = University.query

    if query:
        search_term = f"%{query}%"
        results = results.filter(or_(
            University.name.ilike(search_term),
            University.city.ilike(search_term),
            University.country.ilike(search_term)
        ))

    if region:
        results = results.filter(University.region.ilike(f"%{region}%"))

    if country:
        results = results.filter(University.country.ilike(f"%{country}%"))

    if city:
        results = results.filter(University.city.ilike(f"%{city}%"))

    if min_rank_str.isdigit():
        min_rank = int(min_rank_str)
        # Filter out None values before comparison
        results = results.filter(University.regional_rank != None, University.regional_rank >= min_rank)

    if max_acceptance_str.isdigit():
        max_acceptance = int(max_acceptance_str)
        # Filter out None values before comparison
        results = results.filter(University.acceptance_rate != None, University.acceptance_rate <= max_acceptance)

    if uni_type:
        results = results.filter(University.type.ilike(f"%{uni_type}%"))

    # Only execute query if search parameters were provided
    if request.args:
        final_results = results.order_by(University.name).all()
    else:
        final_results = [] # No search performed yet

    return render_template("search.html", title="Search Results", results=final_results)

@app.route("/compare")
def compare_page():
    # Logic for comparison will be added in step 007
    all_universities = University.query.order_by(University.name).all()
    uni1_id_str = request.args.get("uni1", "")
    uni2_id_str = request.args.get("uni2", "")

    uni1 = None
    uni2 = None
    uni1_id = None
    uni2_id = None

    if uni1_id_str.isdigit():
        uni1_id = int(uni1_id_str)
        uni1 = University.query.get(uni1_id)
    if uni2_id_str.isdigit():
        uni2_id = int(uni2_id_str)
        uni2 = University.query.get(uni2_id)

    return render_template("compare.html", title="Compare Universities",
                           all_universities=all_universities,
                           uni1=uni1, uni2=uni2,
                           uni1_id=uni1_id, uni2_id=uni2_id)

# Add route for adding/removing favorites (Requires POST method and login)
@app.route("/toggle_favorite/<int:university_id>", methods=["POST"])
@login_required
def toggle_favorite(university_id):
    university = University.query.get_or_404(university_id)
    if university in current_user.favorites:
        current_user.favorites.remove(university)
        flash(f"{university.name} removed from favorites.", "success")
    else:
        current_user.favorites.append(university)
        flash(f"{university.name} added to favorites.", "success")
    db.session.commit()
    # Redirect back to the page the user was on, or the university page as fallback
    return redirect(request.referrer or url_for("university_page", university_id=university_id))


if __name__ == "__main__":
    # Create tables if they don't exist (important for first run)
    with app.app_context():
        db.create_all()
    # Note: For deployment, use a production WSGI server like Gunicorn
    app.run(host="0.0.0.0", port=5002, debug=True)

