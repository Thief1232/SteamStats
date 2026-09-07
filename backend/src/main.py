from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)