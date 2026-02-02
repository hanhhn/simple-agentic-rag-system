# Scripts Guide

## Scripts để tải và test Granite Embedding Model

### 1. Tải model về local (Download Model)

Chạy script này để tải Granite embedding model từ Hugging Face về local cache:

```bash
# Chỉ tải model
python scripts/download_model.py --download

# Tải và kiểm tra model
python scripts/download_model.py --download --verify

# Hoặc mặc định (cả hai)
python scripts/download_model.py
```

**Kết quả:**
- Model sẽ được tải về: `data/models/`
- Kích thước: ~95 MB
- Tên folder: `models--ibm-granite--granite-embedding-small-english-r2`

### 2. Test model

Sau khi tải model, chạy test để đảm bảo hoạt động đúng:

```bash
# Chạy full test suite
python scripts/test_embedding.py
```

**Test bao gồm:**
- ✓ Basic encoding (một văn bản)
- ✓ Batch encoding (nhiều văn bản)
- ✓ Similarity computation
- ✓ Long context handling (văn bản dài)
- ✓ Model information

### 3. Kiểm tra model đã tải

Kiểm tra xem model đã được tải chưa:

```bash
# Linux/Mac
ls -lh data/models/

# Windows
dir data\models
```

Nếu model đã tải, sẽ thấy:
```
data/models/models--ibm-granite--granite-embedding-small-english-r2/
├── config.json
├── model.safetensors
├── tokenizer.json
├── tokenizer_config.json
...
```

### 4. Sử dụng model trong code

Sau khi tải model xong, có thể sử dụng như sau:

```python
from src.embedding.models.granite_embedding import GraniteEmbeddingModel

# Model sẽ tự load từ cache
model = GraniteEmbeddingModel()
embedding = model.encode_single("Xin chào")

print(f"Dimension: {len(embedding)}")  # 384
```

### 5. Troubleshooting

#### Lỗi: "Failed to download model"

**Nguyên nhân:**
- Không có internet
- Kết nối mạng không ổn định
- Hugging Face server down

**Giải pháp:**
```bash
# Kiểm tra internet
ping huggingface.co

# Thử lại sau
python scripts/download_model.py
```

#### Lỗi: "CUDA out of memory"

**Nguyên nhân:**
- GPU không đủ VRAM cho Granite model

**Giải pháp:**
```bash
# Sửa config trong .env
EMBEDDING_BATCH_SIZE=16  # Giảm batch size
```

#### Lỗi: "Model not found"

**Nguyên nhân:**
- Model chưa được tải về local

**Giải pháp:**
```bash
# Tải model trước
python scripts/download_model.py

# Sau đó test lại
python scripts/test_embedding.py
```

### 6. Thông tin về Granite Embedding Model

| Thuộc tính | Giá trị |
|------------|----------|
| Model Name | ibm-granite/granite-embedding-small-english-r2 |
| Dimension | 384 |
| Max Context Length | 8192 tokens |
| Supported Languages | English (tối ưu cho tiếng Anh) |
| Model Size | ~95 MB |
| Cache Location | `data/models/` |

### 7. Ví dụ sử dụng

#### Ví dụ 1: Single encoding
```python
from src.embedding.models.granite_embedding import GraniteEmbeddingModel

model = GraniteEmbeddingModel()
embedding = model.encode_single("Học máy là một nhánh của AI")
print(f"Embedding: {embedding[:10]}...")
```

#### Ví dụ 2: Batch encoding
```python
texts = [
    "Xin chào",
    "Hello world",
    "Bonjour le monde"
]

embeddings = model.encode(texts)
for text, emb in zip(texts, embeddings):
    print(f"{text}: {len(emb)} dimensions")
```

#### Ví dụ 3: Tính similarity
```python
emb1 = model.encode_single("Học máy")
emb2 = model.encode_single("Machine learning")

similarity = model.compute_similarity(emb1, emb2)
print(f"Similarity: {similarity:.4f}")
```

## Quick Start

1. Tải model:
   ```bash
   python scripts/download_model.py
   ```

2. Test model:
   ```bash
   python scripts/test_embedding.py
   ```

3. Sử dụng trong code:
   ```python
   from src.embedding.models.granite_embedding import GraniteEmbeddingModel
   model = GraniteEmbeddingModel()
   # Sử dụng model...
   ```

## Lưu ý

- Model chỉ cần tải **một lần** đầu tiên
- Sau đó sẽ được cache trong `data/models/`
- Khi khởi động app, model sẽ load từ cache (nhanh hơn)
- Nếu muốn tải lại model, xóa folder `data/models/models--ibm-granite--granite-embedding-small-english-r2/` và chạy lại script download
