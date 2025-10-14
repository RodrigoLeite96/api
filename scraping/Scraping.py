import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pandas import DataFrame
from sqlalchemy.orm import Session

from utils.Constants import (
    BOOKS_TO_SCRAPE_URL,
    RATING_MAP,
    SLEEP
)

class Scraping():

    def __init__(self) -> None:

        self._response = requests.get(BOOKS_TO_SCRAPE_URL)
        self._soup = BeautifulSoup(requests.get(BOOKS_TO_SCRAPE_URL).text, "html.parser")


    def get_soup(self, url: str) -> BeautifulSoup:
        time.sleep(SLEEP)
        session = requests.Session()
        r = session.get(url, timeout=20)
        r.raise_for_status()
        # return BeautifulSoup(r.text, "lxml")
        return BeautifulSoup(r.text, "html.parser")
    # ---------- PARSERS ----------
    def parse_book_card(self, card, base_url: str, category: str) -> dict:
        a = card.select_one("h3 a")
        title = a.get("title", "").strip()
        product_url = urljoin(base_url, a.get("href"))

        price_el = card.select_one("p.price_color")
        price = price_el.get_text(strip=True) if price_el else None

        avail_el = card.select_one("p.instock.availability")
        availability = avail_el.get_text(strip=True) if avail_el else None

        rating = None
        rating_p = card.select_one("p.star-rating")
        if rating_p:
            for cls in rating_p.get("class", []):
                if cls in RATING_MAP:
                    rating = RATING_MAP[cls]
                    break

        img = card.select_one("div.image_container img")
        image_url = urljoin(base_url, img.get("src")) if img else None

        return {
            "title": title,
            "price": price,
            "availability": availability,
            "rating": rating,
            "category": category,
            "product_url": product_url,
            "image_url": image_url,
        }

    def extract_category_from_listing(self, soup: BeautifulSoup, listing_url: str) -> str | None:
        # 1) Prefer breadcrumb active item (category pages)
        active = soup.select_one("ul.breadcrumb li.active")
        if active:
            cat = active.get_text(strip=True)
            if cat and cat.lower() not in {"home", "books", "all products"}:
                return cat
        # 2) Fallback: infer from URL slug /category/books/<slug>_<id>/
        path = urlparse(listing_url).path
        if "/category/books/" in path:
            part = path.split("/category/books/", 1)[1]
            slug = part.split("/", 1)[0]  # e.g., 'travel_2'
            name = slug.rsplit("_", 1)[0].replace("-", " ").strip()
            if name:
                return name.title()
        return None

    def parse_category_page(self, url: str, known_category: str | None = None):
        soup = self.get_soup(url)
        category = known_category or self.extract_category_from_listing(soup, url)

        cards = soup.select("article.product_pod")
        rows = [self.parse_book_card(card, url, category=category) for card in cards]

        next_a = soup.select_one("li.next > a")
        next_url = urljoin(url, next_a["href"]) if next_a else None
        return rows, next_url, category

    # ---------- CATEGORY DISCOVERY ----------
    def get_all_categories(self, start_url: str = BOOKS_TO_SCRAPE_URL) -> list[tuple[str, str]]:
        soup = self.get_soup(start_url)
        # Sidebar categories
        cats = []
        for a in soup.select("div.side_categories ul li ul li a"):
            name = a.get_text(strip=True)
            href = urljoin(start_url, a.get("href"))
            cats.append((name, href))
        return cats

    # ---------- CRAWLERS ----------
    def crawl_category(self, name: str, url: str) -> list[dict]:
        rows, all_rows = [], []
        while url:
            rows, url, detected = self.parse_category_page(url, known_category=name)
            # If the sidebar name differs slightly, prefer detected (breadcrumb)
            cat_name = detected or name
            for r in rows:
                r["category"] = cat_name
            all_rows.extend(rows)
            print(f"[{cat_name}] total so far: {len(all_rows)}")
        return all_rows

    def crawl_all_books(self, start_url: str = BOOKS_TO_SCRAPE_URL) -> list[dict]:
        all_rows = []
        for name, url in self.get_all_categories(start_url):
            all_rows.extend(self.crawl_category(name, url))
        return all_rows
    
    def save_to_dataframe(self) -> DataFrame:
        """
        """

        books = self.crawl_all_books()
        dataframe = pd.DataFrame(books)
        return dataframe


    def save_to_csv(self) -> None:
        """
        """

        books = self.crawl_all_books()
        dataframe = pd.DataFrame(books)
        dataframe.to_csv("books_all_pages.csv", index=False, encoding="utf-8")
        print(f"Saved {len(dataframe)} books to landing/books_all_pages.csv")


    def get_categories(self):
        """
        """

        links = self._soup.select("ul.nav-list > li > ul > li > a")
        categories = []

        for link in links:
            name = link.get_text(strip=True)
            categories.append(name)

        return print(categories)
    
    def add_to_database(self, db_session: Session, Books, df: DataFrame):
        """
        Inserts book records from a DataFrame into the database.
        Avoids duplicates based on title.
        ---
        Args:
            db_session (Session): SQLAlchemy session instance.
            Books (Base): SQLAlchemy model class for Books.
            df (pd.DataFrame): DataFrame with book data.
        """
        try:
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

            db_session.commit()
            print(f"✅ Successfully added new books to database ({len(df)} rows processed).")

        except Exception as e:
            db_session.rollback()
            print(f"❌ Error inserting data: {e}")
            raise
