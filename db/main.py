from fastapi import FastAPI
from db.core.database import Base, engine
from db.api.books import router as books_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book API")
app.include_router(books_router)
