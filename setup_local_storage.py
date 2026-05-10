from azure.storage.blob import BlobServiceClient
import os

connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"

try:
    service_client = BlobServiceClient.from_connection_string(connection_string)
    containers = ["c1raw", "c2raw", "reconciled"]
    for container in containers:
        try:
            service_client.create_container(container)
            print(f"Created container: {container}")
        except Exception as e:
            print(f"Container {container} already exists or error: {e}")

    # Upload sample data
    with open("dataset/s1_raw.csv", "rb") as data:
        service_client.get_blob_client(container="c1raw", blob="s1_raw.csv").upload_blob(data, overwrite=True)
    print("Uploaded s1_raw.csv to c1raw")

    with open("dataset/s2_raw.csv", "rb") as data:
        service_client.get_blob_client(container="c2raw", blob="s2_raw.csv").upload_blob(data, overwrite=True)
    print("Uploaded s2_raw.csv to c2raw")

except Exception as e:
    print(f"Failed to setup storage: {e}")
