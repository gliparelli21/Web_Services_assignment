import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError


load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "products_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "products")

mongo_client: MongoClient | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global mongo_client
    yield
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None


app = FastAPI(title="Products API", version="1.0.0", lifespan=lifespan)


ProductIdPath = Annotated[int, Path(..., ge=1, description="Product ID (positive integer)")]
StartsWithPath = Annotated[
    str,
    Path(
        ...,
        min_length=1,
        max_length=1,
        pattern=r"^[A-Za-z]$",
        description="Single alphabetic character.",
    ),
]
StartIdQuery = Annotated[int, Query(..., ge=1, description="Starting ProductID (inclusive)")]
EndIdQuery = Annotated[int, Query(..., ge=1, description="Ending ProductID (inclusive)")]


class Product(BaseModel):
    ProductID: int = Field(..., ge=1)
    Name: str
    UnitPrice: float = Field(..., ge=0)
    StockQuantity: int = Field(..., ge=0)
    Description: str


class ProductWithMongoId(Product):
    id: str


def _build_client() -> MongoClient:
    if not MONGODB_URI:
        raise HTTPException(status_code=500, detail="MONGODB_URI is not configured.")
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        return client
    except ServerSelectionTimeoutError as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB connection timeout: {exc}") from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=f"MongoDB configuration error: {exc}") from exc
    except OperationFailure as exc:
        raise HTTPException(status_code=401, detail=f"MongoDB authentication error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MongoDB connection error: {exc}") from exc


def _get_collection() -> Collection:
    global mongo_client
    if mongo_client is None:
        try:
            mongo_client = _build_client()
        except HTTPException:
            raise
    return mongo_client[DB_NAME][COLLECTION_NAME]


def _serialize_product(document: dict[str, Any]) -> ProductWithMongoId:
    return ProductWithMongoId(
        id=str(document["_id"]),
        ProductID=document["ProductID"],
        Name=document["Name"],
        UnitPrice=document["UnitPrice"],
        StockQuantity=document["StockQuantity"],
        Description=document["Description"],
    )


@app.get("/getSingleProduct/{product_id}", response_model=ProductWithMongoId)
def get_single_product(product_id: ProductIdPath) -> ProductWithMongoId:
    collection = _get_collection()
    product = collection.find_one({"ProductID": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return _serialize_product(product)


@app.get("/getAll", response_model=list[ProductWithMongoId])
def get_all_products() -> list[ProductWithMongoId]:
    collection = _get_collection()
    products = collection.find({}).sort("ProductID", 1)
    return [_serialize_product(product) for product in products]


@app.post("/addNew", response_model=ProductWithMongoId, status_code=201)
def add_new_product(product: Product) -> ProductWithMongoId:
    collection = _get_collection()
    existing = collection.find_one({"ProductID": product.ProductID})
    if existing:
        raise HTTPException(status_code=409, detail="A product with this ProductID already exists.")

    payload = product.model_dump()
    insert_result = collection.insert_one(payload)
    inserted = collection.find_one({"_id": insert_result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="Product was inserted but could not be read back.")
    return _serialize_product(inserted)


@app.delete("/deleteOne/{product_id}")
def delete_one_product(product_id: ProductIdPath) -> dict[str, Any]:
    collection = _get_collection()
    result = collection.delete_one({"ProductID": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"deleted": True, "product_id": product_id}


@app.get("/startsWith/{letter}", response_model=list[ProductWithMongoId])
def get_products_starting_with(letter: StartsWithPath) -> list[ProductWithMongoId]:
    collection = _get_collection()
    products = collection.find({"Name": {"$regex": f"^{letter}", "$options": "i"}}).sort("ProductID", 1)
    return [_serialize_product(product) for product in products]


@app.get("/paginate", response_model=list[ProductWithMongoId])
def paginate_products(
    start_id: StartIdQuery,
    end_id: EndIdQuery,
) -> list[ProductWithMongoId]:
    if start_id > end_id:
        raise HTTPException(status_code=400, detail="start_id must be less than or equal to end_id.")

    collection = _get_collection()
    products = (
        collection.find({"ProductID": {"$gte": start_id, "$lte": end_id}})
        .sort("ProductID", 1)
        .limit(10)
    )
    return [_serialize_product(product) for product in products]


@app.get("/convert/{product_id}")
def convert_price_to_eur(product_id: ProductIdPath) -> dict[str, Any]:
    collection = _get_collection()
    product = collection.find_one({"ProductID": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    usd_price = float(product["UnitPrice"])
    try:
        response = httpx.get(
            "https://api.exchangerate.host/latest",
            params={"base": "USD", "symbols": "EUR"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success", True):
            raise ValueError("API returned success=false")
        rate = data["rates"]["EUR"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch exchange rate: {exc}") from exc

    eur_price = round(usd_price * float(rate), 2)
    return {
        "ProductID": product_id,
        "Name": product["Name"],
        "price_usd": usd_price,
        "price_eur": eur_price,
        "rate": rate,
    }