import os
import logging
import datetime
import jwt
from functools import wraps
from flask import Flask, request, jsonify
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

from scraping.Scraping import Scraping
from utils.Config import Config

# =============================
# 🔐 JWT CONFIGURATION
# =============================
JWT_SECRET = "MEUSEGREDOAQUI"
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_modelo")

# =============================
# 🧱 DATABASE CONFIGURATION
# =============================
os.makedirs("/tmp", exist_ok=True)
DB_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/predictions.db")

connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, echo=False, connect_args=connect_args)
Base = declarative_base()
SessionLocal = scoped_session(sessionmaker(bind=engine))

# =============================
# 🧩 MODELS
# =============================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)

class Books(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String(260), nullable=False)
    category = Column(String(120), nullable=False)
    availability = Column(String(120), nullable=True)
    rating = Column(String(1000), nullable=True)
    product_url = Column(String(1000), nullable=True)
    image_url = Column(String(1000), nullable=True)

Base.metadata.create_all(engine)

# =============================
# ⚙️ APP SETUP
# =============================
app = Flask(__name__, instance_path="/tmp/instance")
cfg = Config()
app.config.from_object(cfg)
swagger = Swagger(app)
scraping = Scraping()

TEST_USERNAME = "admin"
TEST_PASSWORD = "secret"

# =============================
# 🔑 JWT HELPERS
# =============================
def create_token(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token ausente"}), 401
        token = auth_header.split(" ")[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated
# Dependency to get a session safely
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================
# 🌐 ROUTES
# =============================
@app.route("/")
def home():
    return jsonify({"msg": "Bem vindo ao Catálogo de Livros Pós Tech - Fiap"})

@app.route("/api/v1/scraping/trigger", methods=["POST"])
@token_required  # Optional: protect it so only authenticated users can trigger scraping
def trigger_scraping():
    """
    Trigger web scraping and save books to database.
    ---
    tags:
      - Scraping
    responses:
      200:
        description: Successfully scraped and saved books
      500:
        description: Error during scraping or database insertion
    """
    db_session = SessionLocal()

    try:
        # Run scraping logic (returns a DataFrame)
        df = scraping.save_to_dataframe()
        if df is None or df.empty:
            return jsonify({"msg": "No data scraped"}), 400

        inserted_count = 0

        for _, row in df.iterrows():
            exists = db_session.query(Books).filter(Books.title == row["title"]).first()
            if not exists:
                book = Books(
                    title=row["title"],
                    category=row["category"],
                    availability=row["availability"],
                    rating=row["rating"],
                    product_url=row["product_url"],
                    image_url=row["image_url"],
                )
                db_session.add(book)
                inserted_count += 1

        db_session.commit()

        return jsonify({
            "msg": f"✅ Successfully added {inserted_count} new books",
            "total_processed": len(df)
        }), 200

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error inserting data: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        db_session.close()


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
    """
    return jsonify({"message": "Olá!"})

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
          required: [username, password]
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
      400:
        description: User already exists
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = SessionLocal()
    try:
        # ✅ Manual query (since no Flask-SQLAlchemy)
        user = db.query(User).filter(User.username == username).first()
        if user:
            return jsonify({"error": "User already exists"}), 400

        hashed = generate_password_hash(password)
        new_user = User(username=username, password=hashed)
        db.add(new_user)
        db.commit()
        return jsonify({"msg": "User created"}), 201
    except Exception as e:
        db.rollback()
        logger.exception("Error registering user")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


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
          required: [username, password]
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
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not check_password_hash(user.password, password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = create_token(user.username)
        return jsonify({"access_token": token}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/api/v1/books/<int:book_id>", methods=["GET"])
@token_required
def get_book(book_id):
    """
    Get book details by ID.
    ---
    tags:
      - Books
    """
    db = SessionLocal()
    try:
        book = db.query(Books).get(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify({
            "id": book.id,
            "title": book.title,
            "category": book.category,
            "availability": book.availability,
            "rating": book.rating,
            "product_url": book.product_url,
            "image_url": book.image_url
        }), 200
    finally:
        db.close()


@app.route("/api/v1/categories", methods=["GET"])
@token_required
def list_categories():
    """
    Get a list of all available book categories.
    ---
    tags:
      - Categories
    """
    db = SessionLocal()
    try:
        categories = db.query(Books.category).distinct().all()
        categories_list = [c[0] for c in categories if c[0]]

        if not categories_list:
            return jsonify({"msg": "No categories found"}), 404

        return jsonify({"categories": categories_list}), 200
    finally:
        db.close()


@app.route("/api/v1/books", methods=["GET"])
@token_required
def list_books():
    """
    List all books (JWT Protected).
    ---
    tags:
      - Books
    """
    db = SessionLocal()
    try:
        books = db.query(Books).all()
        if not books:
            return jsonify({"msg": "No books found"}), 404

        return jsonify([
            {
                "id": b.id,
                "title": b.title,
                "category": b.category,
                "availability": b.availability,
                "rating": b.rating,
                "product_url": b.product_url,
                "image_url": b.image_url,
            } for b in books
        ]), 200
    finally:
        db.close()


@app.route("/api/v1/books/search", methods=["GET"])
@token_required
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
      - name: category
        in: query
        type: string
    """
    title = request.args.get("title")
    category = request.args.get("category")

    db = SessionLocal()
    try:
        query = db.query(Books)

        if title:
            query = query.filter(Books.title.ilike(f"%{title}%"))
        if category:
            query = query.filter(Books.category.ilike(f"%{category}%"))

        results = query.all()
        if not results:
            return jsonify({"msg": "No books found"}), 404

        return jsonify([
            {
                "id": book.id,
                "title": book.title,
                "category": book.category,
                "availability": book.availability,
                "rating": book.rating,
                "product_url": book.product_url,
                "image_url": book.image_url
            } for book in results
        ]), 200
    finally:
        db.close()


if __name__ == "__main__":
    
    scraping.save_to_csv()
    # df = scraping.save_to_dataframe()
    # db_session = SessionLocal()

    with app.app_context():
        # scraping.add_to_database(db_session, Books, df)
        app.run(debug=True)
