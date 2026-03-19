import os
import csv
import json
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError, OperationFailure
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection string from environment variable
MONGODB_URI = os.getenv('MONGODB_URI')

if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in .env file")


def get_database_and_collection(client):
    db_name = os.getenv('DB_NAME', 'products_db')
    collection_name = os.getenv('COLLECTION_NAME', 'products')
    return client[db_name], db_name, collection_name


def export_products_to_json(collection, output_path):
    """
    Reads all documents from MongoDB collection and writes them to a JSON file.
    """
    documents = list(collection.find({}))
    for doc in documents:
        # Convert ObjectId to string for JSON serialization.
        doc['_id'] = str(doc['_id'])

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(documents, json_file, indent=2, ensure_ascii=False)

    print(f"Exported {len(documents)} documents to {output_path}")

def upload_products_to_mongodb():
    """
    Reads products.csv and uploads data to MongoDB cluster
    """
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = MongoClient(MONGODB_URI)
        
        # Test connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        
        # Select database and collection
        db, db_name, collection_name = get_database_and_collection(client)
        collection = db[collection_name]
        
        # Read CSV file
        csv_path = os.path.join('data', 'products.csv')
        products = []
        
        print(f"Reading data from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # Convert data types
                product = {
                    'ProductID': int(row['ProductID']),
                    'Name': row['Name'],
                    'UnitPrice': float(row['UnitPrice']),
                    'StockQuantity': int(row['StockQuantity']),
                    'Description': row['Description']
                }
                products.append(product)
        
        print(f"Found {len(products)} products to upload")
        
        # Clear existing data (optional - remove these lines if you want to append)
        existing_count = collection.count_documents({})
        if existing_count > 0:
            print(f"Clearing {existing_count} existing documents...")
            collection.delete_many({})
        
        # Insert products into MongoDB
        if products:
            result = collection.insert_many(products)
            print(f"Successfully inserted {len(result.inserted_ids)} products!")
            print(f"Database: {db_name}")
            print(f"Collection: {collection_name}")

            # Read documents back from MongoDB and export to local JSON.
            json_output_path = os.getenv('JSON_OUTPUT_PATH', os.path.join('data', 'products_from_mongodb.json'))
            export_products_to_json(collection, json_output_path)
        else:
            print("No products to insert")
        
        # Close connection
        client.close()
        print("Connection closed.")
        
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}")
    except ServerSelectionTimeoutError as e:
        print(f"Connection timeout: {str(e)}")
    except OperationFailure as e:
        print(f"Authentication/authorization error: {str(e)}")
    except ConfigurationError as e:
        print(f"MongoDB configuration error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    upload_products_to_mongodb()
