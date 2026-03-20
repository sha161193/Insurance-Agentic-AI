import os
from dotenv import load_dotenv
from openai import OpenAI
import time
from creating_postgres_database import get_insurance_data_for_embeddings
from milvus_adapter import get_milvus_client

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COLLECTION_NAME = "insurance_customers"
DIMENSION = 1536


def create_milvus_collection(client):
    """Create collection using MilvusClient API (works for both cloud and local)."""
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        dimension=DIMENSION,
        primary_field_name="id",
        vector_field_name="embedding",
        auto_id=True,
        metric_type="L2",
    )
    print(f"✅ Collection '{COLLECTION_NAME}' created.")


def generate_embeddings(data):
    """Generate embeddings using OpenAI's text-embedding-3-large model."""
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
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    for i in range(0, len(texts), batch_size):
        response = openai_client.embeddings.create(
            input=texts[i:i + batch_size],
            model="text-embedding-3-large",
            dimensions=DIMENSION
        )
        embeddings.extend([e.embedding for e in response.data])
        time.sleep(1)

    return embeddings


def main():
    # Step 1: Get data from PostgreSQL
    insurance_data = get_insurance_data_for_embeddings()
    if not insurance_data:
        print("No data retrieved from PostgreSQL")
        return

    # Step 2: Connect to Milvus (cloud or local automatically)
    client = get_milvus_client()
    create_milvus_collection(client)

    # Step 3: Generate embeddings
    print("Generating embeddings...")
    embeddings = generate_embeddings(insurance_data)

    # Step 4: Insert into Milvus using MilvusClient API
    print("Inserting embeddings into Milvus...")
    entities = []
    for i, item in enumerate(insurance_data):
        entities.append({
            "embedding":     embeddings[i],
            "customer_id":   item['customer_id'],
            "customer_name": item['customer_name'],
            "policy_types":  item['policy_types'],
            "metadata": {
                "email":            item['email'],
                "phone":            item['phone_number'],
                "address":          item['full_address'],
                "dob":              item['date_of_birth'],
                "life_beneficiary": item['life_beneficiary'],
                "life_sum_assured": item['life_sum_assured'],
                "home_address":     item['home_address'],
                "home_value":       item['home_value'],
                "vehicle":          item['vehicle'],
                "vehicle_year":     item['vehicle_year'],
            }
        })

    client.insert(collection_name=COLLECTION_NAME, data=entities)
    print(f"✅ Inserted {len(insurance_data)} embeddings into Milvus")


if __name__ == "__main__":
    main()
