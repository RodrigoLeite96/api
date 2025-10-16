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
    """
    Um scraper para o site de demonstração Books to Scrape.

    Fornece métodos para:
    • Analisar fichas e categorias de livros.
    • Rastrear recursivamente todas as páginas de categorias.
    • Salvar os resultados em um DataFrame ou arquivo CSV do Pandas.
    """

    def __init__(self) -> None:

        self._response = requests.get(BOOKS_TO_SCRAPE_URL)
        self._soup = BeautifulSoup(requests.get(BOOKS_TO_SCRAPE_URL).text, "html.parser")


    def get_soup(self, url: str) -> BeautifulSoup:
        """
        Busca e analisa HTML de uma URL fornecida.

        Args:
        url (str): URL da página de destino.

        Return:
        BeautifulSoup: Conteúdo HTML analisado da página.

        Raise:
        requests.exceptions.RequestException: Se a solicitação falhar.
        """

        time.sleep(SLEEP)
        session = requests.Session()
        r = session.get(url, timeout=20)
        r.raise_for_status()

        return BeautifulSoup(r.text, "html.parser")


    def parse_book_card(self, card, base_url: str, category: str) -> dict:
        """
        Extrai detalhes do livro de um cartão de produto individual.

        Args:
            card (Tag): A tag HTML contendo um cartão de livro.
            base_url (str): URL da página atual para unir links relativos.
            category (str): Nome da categoria do anúncio atual.

        Returns:
            dict: Dicionário com campos analisados:
                {
                    "title": str,
                    "price": str,
                    "availability": str,
                    "rating": int | None,
                    "category": str,
                    "product_url": str,
                    "image_url": str
                }
        """

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
        """
        Determina o nome da categoria a partir da página de listagem.

        Primeiro, verifica o elemento de trilha de navegação e retorna
        à análise da estrutura da URL, se necessário.

        Args:
            soup (BeautifulSoup): HTML analisado da página da categoria.
            listing_url (str): URL da página atual.

        Returns:
            str | None: O nome da categoria, se encontrado; caso contrário, None.
        """

        active = soup.select_one("ul.breadcrumb li.active")
        if active:
            cat = active.get_text(strip=True)
            if cat and cat.lower() not in {"home", "books", "all products"}:
                return cat


        path = urlparse(listing_url).path
        if "/category/books/" in path:
            part = path.split("/category/books/", 1)[1]
            slug = part.split("/", 1)[0]
            name = slug.rsplit("_", 1)[0].replace("-", " ").strip()
            if name:
                return name.title()
        return None

    def parse_category_page(self, url: str, known_category: str | None = None):
        """
        Analisa uma página de categoria, extraindo todos os cards de livros e o link para a próxima página.

        Args:
            url (str): URL da página da categoria a ser analisada.
            known_category (str | None, optional): Nome da categoria predefinido. O padrão é None, nesse caso, tenta detectar automaticamente.

        Returns:
            tuple[list[dict], str | None, str]:
            - Lista de livros (cada um como dict)
            - URL da próxima página (se existir, caso contrário, None)
            - Nome da categoria detectada
        """

        soup = self.get_soup(url)
        category = known_category or self.extract_category_from_listing(soup, url)

        cards = soup.select("article.product_pod")
        rows = [self.parse_book_card(card, url, category=category) for card in cards]

        next_a = soup.select_one("li.next > a")
        next_url = urljoin(url, next_a["href"]) if next_a else None
        return rows, next_url, category


    def get_all_categories(self, start_url: str = BOOKS_TO_SCRAPE_URL) -> list[tuple[str, str]]:
        """
        Recupera todos os nomes de categorias e suas URLs da barra lateral da página inicial.

        Args:
            start_url (str, optional): URL do site principal. O padrão é BOOKS_TO_SCRAPE_URL.

        Returns:
            list[tuple[str, str]]: Lista de pares (category_name, category_url).
        """

        soup = self.get_soup(start_url)
 
        cats = []
        for a in soup.select("div.side_categories ul li ul li a"):
            name = a.get_text(strip=True)
            href = urljoin(start_url, a.get("href"))
            cats.append((name, href))
        return cats


    def crawl_category(self, name: str, url: str) -> list[dict]:
        """
        Rastreia recursivamente todas as páginas dentro de uma única categoria.

        Args:
            name (str): Nome da categoria (da barra lateral ou detectado).
            url (str): URL da categoria a partir da qual iniciar o rastreamento.

        Returns:
            list[dict]: Lista de todos os dicionários de livros dentro dessa categoria.
        """
        
        rows, all_rows = [], []
        while url:
            rows, url, detected = self.parse_category_page(url, known_category=name)
 
            cat_name = detected or name
            for r in rows:
                r["category"] = cat_name
            all_rows.extend(rows)
            print(f"[{cat_name}] total so far: {len(all_rows)}")
        return all_rows

    def crawl_all_books(self, start_url: str = BOOKS_TO_SCRAPE_URL) -> list[dict]:
        """
        Rastreia todas as categorias do site e extrai todos os livros.

        Args:
            start_url (str, optional): URL raiz para iniciar a descoberta. O padrão é BOOKS_TO_SCRAPE_URL.

        Returns:
            list[dict]: Lista combinada de todos os livros encontrados no site.
        """

        all_rows = []
        for name, url in self.get_all_categories(start_url):
            all_rows.extend(self.crawl_category(name, url))
        return all_rows
    
    def save_to_dataframe(self) -> DataFrame:
        """
        Rastreia todas as categorias e retorna os resultados como um DataFrame do Pandas.

        Returns:
            DataFrame: Um DataFrame contendo todos os livros.
        """

        books = self.crawl_all_books()
        dataframe = pd.DataFrame(books)
        return dataframe


    def save_to_csv(self) -> None:
        """
        Rastreia todas as categorias e salva os resultados em um arquivo CSV.
        O arquivo é salvo em codificação UTF-8 com cabeçalhos e sem coluna de índice.

        Returns:
            None
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