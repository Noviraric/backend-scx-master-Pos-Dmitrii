from sqlalchemy.orm import Session
from db.models.books import Book
from db.schemas.books import BookCreate

class BookRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(Book).all()

    def create(self, data: BookCreate):
        book = Book(title=data.title, author=data.author)
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book
