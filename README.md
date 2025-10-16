# 📚 Book Catalog API

A Flask-based API for scraping book data and serving a RESTful interface with JWT authentication.

---

## 🧩 Table of Contents

- [Features](#features)  
- [Project Structure](#project-structure)  
- [Getting Started](#getting-started)  
  - [Requirements](#requirements)  
  - [Installation](#installation)  
  - [Configuration](#configuration)  
  - [Running Locally](#running-locally)  
- [API Endpoints](#api-endpoints)  
  - [Auth](#auth)  
  - [Books](#books)  
  - [Scraping](#scraping)  
- [Swagger / API Docs](#swagger--api-docs)  
- [Deployment](#deployment)  
- [Contributing](#contributing)  
- [License](#license)

---

## 🎯 Features

- Register / login users (JWT-based authentication)  
- CRUD-style read operations for books: list, get by ID, search by title/category  
- Trigger a scraping job to fetch book data and persist it, avoiding duplicates  
- Swagger / OpenAPI documentation via **Flasgger**  
- Configurable for local SQLite or external databases (PostgreSQL, MySQL, etc.)  
- Deployable to serverless platforms (e.g. Vercel)  

---

## 🗂 Project Structure

.
├── api
│ ├── app.py # main Flask app and route definitions
│ ├── scraping # scraper module (Scraping logic)
│ └── utils # utility modules (e.g. Config)
├── books_all_pages.csv # example or output CSV data
├── requirements.txt
├── vercel.json # Vercel build / routing config
└── README.md


- `app.py` — defines all API routes, JWT handlers, DB setup  
- `scraping/` — contains the logic to fetch and transform book data (e.g. via web scraping)  
- `utils/Config.py` — configuration and settings (e.g. DB URL, JWT settings)  
- `vercel.json` — routing and build settings to host on Vercel  

---

## 🚀 Getting Started

### Requirements

- Python 3.8+  
- `pip`  
- (Optional) PostgreSQL, MySQL, or other DB if not using SQLite locally  

### Installation

```bash
git clone https://github.com/RodrigoLeite96/api.git
cd api
pip install -r requirements.txt

Configuration

Copy .env.example or create an .env file (if you maintain env configs)

Set the following (or use defaults):

Variable	Purpose	Example
DATABASE_URL	Database connection URI	sqlite:////tmp/predictions.db or postgresql://user:pass@host:port/dbname
JWT_SECRET	Secret key for signing tokens	your-super-secret-key
JWT_EXP_DELTA_SECONDS	Token expiry in seconds	3600 (one hour)

Verify vercel.json is configured for serverless deployment (if deploying to Vercel)

Running Locally

export FLASK_APP=app.py
# (if using .env) source .env
flask run
🛠 API Endpoints

Here’s a high-level overview of your API:

Auth
Endpoint	Method	Auth required	Description
/api/v1/auth/register	POST	No	Register a new user
/api/v1/auth/login	POST	No	Login and retrieve JWT token
Books
Endpoint	Method	Auth required	Description
/api/v1/books	GET	Yes	List all books
/api/v1/books/<int:book_id>	GET	Yes	Get a single book by ID
/api/v1/books/search	GET	Yes	Search books by title and/or category query parameters
/api/v1/categories	GET	Yes	List all distinct book categories
Scraping
Endpoint	Method	Auth required	Description
/api/v1/scraping/trigger	POST	Yes (optional)	Trigger scraping to fetch and store new books
📄 Swagger / API Docs

Once the app is running (either locally or deployed), you can access the interactive documentation at:

/apidocs

For example, if deployed at https://api-dun-psi.vercel.app, go to:

https://api-dun-psi.vercel.app/apidocs


Flasgger reads the YAML docstrings in your routes and displays them in the UI, letting you test endpoints directly.

⚙ Deployment

This project is ready to run on Vercel using vercel.json for routing and build instructions.
Typical steps:

Push your code to GitHub

Connect your repo to Vercel

Configure environment variables in Vercel dashboard (e.g. DATABASE_URL, JWT_SECRET)

Deploy — Vercel will auto-build and expose your Flask API at a stable domain.

Also ensure your vercel.json routes all requests to api/app.py (or your entrypoint) so Flask handles them correctly.

🧑‍💻 Contributing

Contributions, bug reports, and feature requests are welcome!

Fork this repository

Create a new branch: git checkout -b feature/awesome-feature

Make your changes & add tests

Run the app locally to verify

Submit a PR with a clear description

Please check code style, docs, and maintain consistency.

📜 License

This project’s license is not specified.
You may add an open-source license of your choice (e.g. MIT, Apache 2.0) to LICENSE.md.

Let me know if you’d like me to generate:

A .env.example file

A BADGES section (coverage, build status)

Live usage examples (curl, Python)

Automatically generated API spec (OpenAPI JSON / YAML)