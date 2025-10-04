from pydantic import BaseModel, Field, ValidationError
import json
from typing import List


class Image(BaseModel):
    filename: str
    caption: str


class ArticleModel(BaseModel):
    pmid: int
    title: str
    journal: str
    year: int
    abstract: str
    introduction: str | None = None
    conclusion: str | None = None
    fulltext: str | None = None
    images: list[Image] = []
    keywords: list[str] = []


def make_json(article_model: ArticleModel) -> str:
    article_json = article_model.model_dump_json(indent=4)
    # print(article_json)
    return article_json


def make_model(raw_data: dict) -> ArticleModel:
    print(raw_data)

    article = ArticleModel(
        pmid=int(raw_data.get("pmid", 0)),
        title=str(raw_data.get("title", "")),
        journal=str(raw_data.get("journal", "")),
        year=int(raw_data.get("year", 0)),
        abstract=str(raw_data.get("abstract", "")),
        introduction=raw_data.get("introduction"),
        conclusion=raw_data.get("conclusion"),
        fulltext=raw_data.get("fulltext"),
        images=raw_data.get("images", []),
        keywords=raw_data.get("keywords", [])
    )

    return article


def read_from_json_file(file_name: str) -> ArticleModel:
    with open(file_name, "r") as f:
        raw_article = json.load(f)[0]
        return make_model(raw_article)


def write_to_json_file(file_name: str, article_model: ArticleModel):
    with open(file_name, "wx") as f:
        f.write(make_json(article_model))
    
try:
    article_model = read_from_json_file("data/25133741/article_data.json")
except ValidationError as err:
    print(err)