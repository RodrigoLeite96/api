import sys


class Config():


    def __init__(self):
        self.SECRET_KEY = "1234"
        self.CACHE_TYPE = "simple"
        self.SWAGGER = {
            'title' : 'Catálogo de Livros',
            'uiversion' : 3
        }
        # self.SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
        self.SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/database.db"
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.JWT_SECRET_KEY = "1234"