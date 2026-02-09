import chromadb
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path

class SchemaVectorStore:
    def __init__(self, collection_name="schema_store"):
        self.client = chromadb.Client() 
        self.collection = self.client.create_collection(name=collection_name)
        self.model = SentenceTransformer('all-MiniLM-L6-v2') 

    def index_profiles(self, profile_dir: str):
        """Đọc JSON profiles và lưu vào Vector DB"""
        p_path = Path(profile_dir)
        files = list(p_path.glob("*.json"))
        
        print(f"[*] Đang Index {len(files)} profiles vào Vector DB...")
        
        ids = []
        documents = []
        metadatas = []

        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                table_name = data['table_name']
                
                keywords = []
                for col in data.get('columns', []):
                    keywords.extend(col.get('suggested_keywords', []))
                
                content = f"Bảng {table_name}. Chứa thông tin: {', '.join(keywords[:20])}"
                
                ids.append(table_name)
                documents.append(content)
                metadatas.append({"path": str(f)})

        if documents:
            self.collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
            print("✅ Index thành công!")

    def search_table(self, query: str, n_results=1):
        """Tìm bảng phù hợp nhất với câu hỏi"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if results['ids'] and results['ids'][0]:
            best_table = results['ids'][0][0]
            profile_path = results['metadatas'][0][0]['path']
            return best_table, profile_path
        return None, None