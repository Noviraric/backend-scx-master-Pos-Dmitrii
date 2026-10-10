from db.repositories.books import BookRepository
from db.schemas.books import BookCreate

class BookService:
    def __init__(self, repo: BookRepository):
        self.repo = repo

    def get_all(self):
        return self.repo.get_all()

    def create(self, data: BookCreate):
        return self.repo.create(data)
