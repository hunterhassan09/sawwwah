# -*- coding: utf-8 -*-
"""
Database models for the University Search Website.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    region = db.Column(db.String(50), nullable=False) # e.g., "Egypt", "Gulf"
    country = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True) # Added for maps
    longitude = db.Column(db.Float, nullable=True) # Added for maps
    certified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float) # Store rating numerically if possible, or String
    founded_year = db.Column(db.Integer)
    type = db.Column(db.String(50)) # Public / Private
    regional_rank = db.Column(db.Integer, nullable=True)
    world_rank = db.Column(db.String(50), nullable=True) # Can be range like "721-730" or "Not Ranked"
    acceptance_rate = db.Column(db.Integer, nullable=True) # Percentage
    igcse_requirements = db.Column(db.Text, nullable=True)
    advantages = db.Column(db.Text, nullable=True)
    disadvantages = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<University {self.name}>"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    favorites = db.relationship("University", secondary="user_favorites", backref=db.backref("favorited_by", lazy="dynamic"))

    def __repr__(self):
        return f"<User {self.username}>"

# Association table for many-to-many relationship between User and University (Favorites)
user_favorites = db.Table("user_favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("university_id", db.Integer, db.ForeignKey("university.id"), primary_key=True)
)

