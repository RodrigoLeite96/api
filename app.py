import os
import logging
import datetime
import jwt
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, 
    create_access_token,
    jwt_required, 
    get_jwt_identity
)
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash

from scraping.Scraping import Scraping
from database.Database import Database
from utils.Config import Config

app = Flask(__name__, instance_path="/tmp/instance")
cfg = Config()
app.config.from_object(cfg)

db = SQLAlchemy(app)
jwt_manager = JWTManager(app)
swagger = Swagger(app)

User, Books = Database(db)


scraping = Scraping()

@app.route('/about')
def about():
    """
    About endpoint
    ---
    tags:
      - Info
    responses:
      200:
        description: Returns a simple greeting message
        examples:
          application/json:
            message: Olá!
    """
    return jsonify({"message": "Olá!"})

@app.route("/")
def home():
    return jsonify({"msg": "Hello from Flask on Vercel!"})

@app.route('/api/v1/auth/register', methods=['POST'])
def register_user():
    """
    Register a new user.
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: johndoe
            password:
              type: string
              example: secret123
    responses:
      201:
        description: User successfully created
        examples:
          application/json:
            msg: User created
      400:
        description: User already exists
        examples:
          application/json:
            error: User already exists
    """
    data = request.get_json()
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User already exists"}), 400

    hashed = generate_password_hash(data["password"])
    new_user = User(username=data["username"], password=hashed)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User created"}), 201


@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    """
    User login to obtain JWT token.
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: "rodrigo"
            password:
              type: string
              example: "123456"
    responses:
      200:
        description: Token returned
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    user = User.query.filter_by(username=data["username"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.username)
    return jsonify({"access_token": access_token}), 200


@app.route("/api/v1/books/<int:book_id>", methods=["GET"])
@jwt_required()
def get_book(book_id):
    """
    Get book details by ID.
    ---
    tags:
      - Books
    parameters:
      - name: book_id
        in: path
        type: integer
        required: true
        description: The unique ID of the book
    responses:
      200:
        description: Book details successfully retrieved
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 1
            title:
              type: string
              example: "The Great Gatsby"
            category:
              type: string
              example: "Classics"
            availability:
              type: string
              example: "In stock"
            rating:
              type: string
              example: "Four"
            product_url:
              type: string
              example: "http://books.toscrape.com/catalogue/the-great-gatsby_1/index.html"
            image_url:
              type: string
              example: "http://books.toscrape.com/media/cache/3e/ef/3eef99c9e.jpg"
      404:
        description: Book not found
        examples:
          application/json:
            error: Book not found
    """
    book = Books.query.get(book_id)

    if not book:
        return jsonify({"error": "Book not found"}), 404

    book_data = {
        "id": book.id,
        "title": book.title,
        "category": book.category,
        "availability": book.availability,
        "rating": book.rating,
        "product_url": book.product_url,
        "image_url": book.image_url,
    }

    return jsonify(book_data), 200


@app.route("/api/v1/categories", methods=["GET"])
@jwt_required()
def list_categories():
    """
    Get a list of all available book categories.
    ---
    tags:
      - Categories
    responses:
      200:
        description: Successfully retrieved list of categories
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: string
              example: ["Classics", "Science", "Fantasy", "Mystery"]
      404:
        description: No categories found
        examples:
          application/json:
            msg: No categories found
    """
    categories = db.session.query(Books.category).distinct().all()
    categories_list = [c[0] for c in categories if c[0] is not None]

    if not categories_list:
        return jsonify({"msg": "No categories found"}), 404

    return jsonify({"categories": categories_list}), 200


@app.route("/api/v1/books", methods=["GET"])
# @jwt_required()
def list_books():
    """
    List all books (JWT Protected).
    ---
    security:
      - Bearer: []
    tags:
      - Books
    responses:
      200:
        description: Successfully retrieved list of books
      401:
        description: Missing or invalid JWT token
    """
    books = Books.query.all()
    if not books:
        return jsonify({"msg": "No books found"}), 404

    return jsonify([
        {
            "id": b.id,
            "title": b.title,
            "category": b.category,
            "availability": b.availability,
            "rating": b.rating
        } for b in books
    ]), 200


@app.route("/api/v1/books/search", methods=["GET"])
@jwt_required()
def search_books():
    """
    Search for books by title and/or category.
    ---
    tags:
      - Books
    parameters:
      - name: title
        in: query
        type: string
        required: false
        description: Filter books by title (case-insensitive, partial match allowed)
        example: "Gatsby"
      - name: category
        in: query
        type: string
        required: false
        description: Filter books by category (case-insensitive, partial match allowed)
        example: "Classics"
    responses:
      200:
        description: Successfully retrieved list of matching books
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 1
              title:
                type: string
                example: "The Great Gatsby"
              category:
                type: string
                example: "Classics"
              availability:
                type: string
                example: "In stock"
              rating:
                type: string
                example: "Four"
              product_url:
                type: string
                example: "http://books.toscrape.com/catalogue/the-great-gatsby_1/index.html"
              image_url:
                type: string
                example: "http://books.toscrape.com/media/cache/3e/ef/3eef99c9e.jpg"
      404:
        description: No books found matching the filters
        examples:
          application/json:
            msg: No books found
    """
    title = request.args.get("title")
    category = request.args.get("category")

    query = Books.query

    if title:
        query = query.filter(Books.title.ilike(f"%{title}%"))
    if category:
        query = query.filter(Books.category.ilike(f"%{category}%"))

    results = query.all()

    if not results:
        return jsonify({"msg": "No books found"}), 404

    books_list = [{
        "id": book.id,
        "title": book.title,
        "category": book.category,
        "availability": book.availability,
        "rating": book.rating,
        "product_url": book.product_url,
        "image_url": book.image_url
    } for book in results]

    return jsonify(books_list), 200


if __name__ == "__main__":
    scraping.save_to_csv()
    df = scraping.save_to_dataframe()
    with app.app_context():
        
        db.create_all()
        
        scraping.add_to_database(db, Books, df)
        app.run(debug=True)
