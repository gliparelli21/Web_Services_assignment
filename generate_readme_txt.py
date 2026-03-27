from datetime import datetime
from pathlib import Path
import zipfile


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


def create_completion_zip() -> None:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    zip_filename = f"complete-{date_str}-{time_str}.zip"
    
    files_to_include = [
        "products_api.py",
        "mongodb.py",
        "Dockerfile.api",
        "requirements.txt",
        "generate_readme_txt.py",
        "README.txt",
        "Jenkinsfile",
    ]
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            file_path = Path(file)
            if file_path.exists():
                zipf.write(file_path, arcname=file)
    
    print(f"Created {zip_filename}")


def main() -> None:
    Path("README.txt").write_text(build_readme_text(), encoding="utf-8")
    create_completion_zip()


if __name__ == "__main__":
    main()
