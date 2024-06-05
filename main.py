from typing import Union
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from Scrapper import Scrapper
from pydantic import BaseModel
from typing import Set
import json


scrapper = Scrapper()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Part Number Scrapper": "Welcome!"}


