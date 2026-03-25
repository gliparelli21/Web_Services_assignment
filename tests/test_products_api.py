from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import products_api


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, field, direction):
        reverse = direction == -1
        self.docs.sort(key=lambda doc: doc[field], reverse=reverse)
        return self

    def limit(self, size):
        self.docs = self.docs[:size]
        return self

    def __iter__(self):
        return iter(self.docs)


class FakeCollection:
    def __init__(self, docs):
        self.docs = [dict(doc) for doc in docs]

    def find_one(self, query):
        if "_id" in query:
            return next((doc for doc in self.docs if doc.get("_id") == query["_id"]), None)

        return next(
            (
                doc
                for doc in self.docs
                if all(doc.get(key) == value for key, value in query.items())
            ),
            None,
        )

    def find(self, query):
        if not query:
            return FakeCursor(self.docs)

        if "Name" in query and "$regex" in query["Name"]:
            pattern = query["Name"]["$regex"].replace("^", "").lower()
            filtered = [doc for doc in self.docs if doc["Name"].lower().startswith(pattern)]
            return FakeCursor(filtered)

        if "ProductID" in query and isinstance(query["ProductID"], dict):
            gte = query["ProductID"].get("$gte", float("-inf"))
            lte = query["ProductID"].get("$lte", float("inf"))
            filtered = [doc for doc in self.docs if gte <= doc["ProductID"] <= lte]
            return FakeCursor(filtered)

        filtered = [doc for doc in self.docs if all(doc.get(key) == value for key, value in query.items())]
        return FakeCursor(filtered)

    def insert_one(self, payload):
        inserted = dict(payload)
        inserted["_id"] = f"id-{payload['ProductID']}"
        self.docs.append(inserted)
        return SimpleNamespace(inserted_id=inserted["_id"])

    def delete_one(self, query):
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if doc.get("ProductID") != query.get("ProductID")]
        deleted_count = before - len(self.docs)
        return SimpleNamespace(deleted_count=deleted_count)


@pytest.fixture(autouse=True)
def patch_lifespan_client(monkeypatch):
    class DummyClient:
        def close(self):
            return None

    monkeypatch.setattr(products_api, "_build_client", lambda: DummyClient())


@pytest.fixture
def base_docs():
    return [
        {
            "_id": "id-1001",
            "ProductID": 1001,
            "Name": "NVIDIA RTX 4090",
            "UnitPrice": 1599.99,
            "StockQuantity": 12,
            "Description": "High-end GPU",
        },
        {
            "_id": "id-1002",
            "ProductID": 1002,
            "Name": "AMD Ryzen 9",
            "UnitPrice": 549.0,
            "StockQuantity": 25,
            "Description": "Desktop processor",
        },
    ]


@pytest.fixture
def client(monkeypatch, base_docs):
    collection = FakeCollection(base_docs)
    monkeypatch.setattr(products_api, "_get_collection", lambda: collection)
    with TestClient(products_api.app) as test_client:
        yield test_client


def test_get_single_product(client):
    response = client.get("/getSingleProduct/1001")
    assert response.status_code == 200
    assert response.json()["ProductID"] == 1001


def test_get_all_products(client):
    response = client.get("/getAll")
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_add_new_product(client):
    response = client.post(
        "/addNew",
        json={
            "ProductID": 2001,
            "Name": "Sample Product",
            "UnitPrice": 10.5,
            "StockQuantity": 3,
            "Description": "Sample",
        },
    )
    assert response.status_code == 201
    assert response.json()["ProductID"] == 2001


def test_delete_one_product(client):
    response = client.delete("/deleteOne/1002")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_starts_with(client):
    response = client.get("/startsWith/N")
    assert response.status_code == 200
    names = [product["Name"] for product in response.json()]
    assert all(name.lower().startswith("n") for name in names)


def test_paginate(client):
    response = client.get("/paginate?start_id=1000&end_id=2000")
    assert response.status_code == 200
    assert len(response.json()) <= 10


def test_convert_price_to_eur(client, monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"rates": {"EUR": 0.9}}

    monkeypatch.setattr(products_api.httpx, "get", lambda *args, **kwargs: FakeResponse())

    response = client.get("/convert/1001")
    assert response.status_code == 200
    body = response.json()
    assert body["ProductID"] == 1001
    assert body["price_eur"] == round(body["price_usd"] * 0.9, 2)
