# SearchTA

V1 benchmark: tìm **canh cá rô / canh cá rô đồng / bún cá rô đồng** gần vị trí người dùng, ưu tiên kết hợp rating cao + nhiều lượt đánh giá + khoảng cách gần.

## Run
1. Copy `.env.example` thành `.env`
2. Điền `GOOGLE_MAPS_API_KEY`
3. `pip install -r requirements.txt`
4. `uvicorn app:app --host 0.0.0.0 --port 8080`

## API
`GET /search?lat=10.77&lng=106.69`

V1 cố tình chỉ giải đúng benchmark này. Search ba biến thể được gọi song song, gộp theo Google Place ID, sau đó xếp hạng bằng rating, log(review count) và khoảng cách Haversine. Response có timing từng pha để đo tốc độ thật.
