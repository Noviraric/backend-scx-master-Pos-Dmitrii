from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.core.database import get_db
from db.schemas.books import BookCreate, BookResponse
from db.repositories.books import BookRepository
from db.services.books import BookService

router = APIRouter(prefix="/books", tags=["books"])

def get_book_service(db: Session = Depends(get_db)):
    return BookService(BookRepository(db))

@router.get("", response_model=List[BookResponse])
def get_books(service: BookService = Depends(get_book_service)):
    return service.get_all()

@router.post("", response_model=BookResponse, status_code=201)
def create_book(data: BookCreate, service: BookService = Depends(get_book_service)):
    return service.create(data)
