from flask_sqlalchemy import SQLAlchemy


def Database(db):
    class User(db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password = db.Column(db.String(120), nullable=False)

        def __repr__(self):
            return f"<User {self.username}>"


    class Books(db.Model):
        __tablename__ = "books"
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(260), nullable=False)
        category = db.Column(db.String(120), nullable=False)
        availability = db.Column(db.String(120), nullable=True)
        rating = db.Column(db.String(1000), nullable=True)
        product_url = db.Column(db.String(1000), nullable=True)
        image_url = db.Column(db.String(1000), nullable=True)

        def __repr__(self):
            return f"<Books {self.title}>"


    return User, Books
