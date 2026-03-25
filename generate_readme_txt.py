from pathlib import Path


ENDPOINTS = [
    ("GET", "/getSingleProduct/{product_id}", "product_id: int (path, >= 1)"),
    ("GET", "/getAll", "No parameters"),
    (
        "POST",
        "/addNew",
        "JSON body: ProductID(int >= 1), Name(str), UnitPrice(float >= 0), StockQuantity(int >= 0), Description(str)",
    ),
    ("DELETE", "/deleteOne/{product_id}", "product_id: int (path, >= 1)"),
    ("GET", "/startsWith/{letter}", "letter: single alphabetic character (path)"),
    ("GET", "/paginate", "start_id: int (query, >= 1), end_id: int (query, >= 1)"),
    ("GET", "/convert/{product_id}", "product_id: int (path, >= 1)"),
]


def build_readme_text() -> str:
    lines = [
        "Products API Endpoint Reference",
        "",
        "FastAPI documentation: http://localhost:8000/docs",
        "",
        "Endpoints:",
    ]

    for method, endpoint, params in ENDPOINTS:
        lines.append(f"- {method} {endpoint}")
        lines.append(f"  Parameters: {params}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    Path("README.txt").write_text(build_readme_text(), encoding="utf-8")


if __name__ == "__main__":
    main()
