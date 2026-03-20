import os
from dotenv import load_dotenv
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
from openai import OpenAI
import time
from creating_postgres_database import get_insurance_data_for_embeddings
from milvus_adapter import get_milvus_client

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COLLECTION_NAME = "insurance_customers"
DIMENSION = 1536  # Dimension for text-embedding-3-large


def create_milvus_collection():
    if utility.has_collection(COLLECTION_NAME):
        utility.drop_collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="customer_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION),
        FieldSchema(name="customer_name", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="policy_types", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="metadata", dtype=DataType.JSON)
    ]

    schema = CollectionSchema(fields, description="Insurance customer embeddings")
    collection = Collection(COLLECTION_NAME, schema)

    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 128}
    }
    collection.create_index("embedding", index_params)
    return collection


def generate_embeddings(data):
    """Generate embeddings using OpenAI's text-embedding-3-large model"""
    texts = []
    for record in data:
        text_parts = [
            f"Customer: {record['customer_name']}",
            f"Policies: {record['policy_types']}",
            f"Premium: ${record['premium_amount']}",
        ]

        if record['life_beneficiary']:
            text_parts.append(f"Life Insurance Beneficiary: {record['life_beneficiary']} (${record['life_sum_assured']})")

        if record['home_address']:
            text_parts.append(f"Home: {record['home_address']} ({record['home_type']}, ${record['home_value']})")

        if record['vehicle']:
            text_parts.append(f"Vehicle: {record['vehicle']} ({record['vehicle_year']})")

        texts.append("\n".join(text_parts))

    embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        response = OpenAI(api_key=OPENAI_API_KEY).embeddings.create(
            input=texts[i:i + batch_size],
            model="text-embedding-3-large",
            dimensions=DIMENSION
        )
        embeddings.extend([e.embedding for e in response.data])
        time.sleep(1)  # Rate limit handling

    return embeddings


def main():
    # Step 1: Get data from PostgreSQL
    insurance_data = get_insurance_data_for_embeddings()
    if not insurance_data:
        print("No data retrieved from PostgreSQL")
        return

    # Step 2: Connect to Milvus (handles cloud vs local automatically)
    get_milvus_client()
    collection = create_milvus_collection()

    # Step 3: Generate embeddings
    print("Generating embeddings...")
    embeddings = generate_embeddings(insurance_data)

    # Step 4: Insert into Milvus
    print("Inserting embeddings into Milvus...")
    entities = [
        [item['customer_id'] for item in insurance_data],       # customer_id
        embeddings,                                              # embedding vectors
        [item['customer_name'] for item in insurance_data],     # customer_name
        [item['policy_types'] for item in insurance_data],      # policy_types
        [{
            'email':            item['email'],
            'phone':            item['phone_number'],
            'address':          item['full_address'],
            'dob':              item['date_of_birth'],
            'life_beneficiary': item['life_beneficiary'],
            'life_sum_assured': item['life_sum_assured'],
            'home_address':     item['home_address'],
            'home_value':       item['home_value'],
            'vehicle':          item['vehicle'],
            'vehicle_year':     item['vehicle_year']
        } for item in insurance_data]                           # metadata
    ]

    collection.insert(entities)
    collection.flush()
    print(f"✅ Inserted {len(insurance_data)} embeddings into Milvus")


if __name__ == "__main__":
    main()
