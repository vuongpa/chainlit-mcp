# Chatbot Hỗ Trợ Khách Hàng với RAG & MCP

Nền tảng chatbot tùy biến cho Oreka giúp đội hỗ trợ khách hàng triển khai trợ lý ảo song ngữ, vừa nắm vững tri thức nội bộ (Retrieval-Augmented Generation) vừa truy xuất dữ liệu nghiệp vụ thời gian thực thông qua Model Context Protocol (MCP). Giải pháp được đóng gói như một ứng dụng FastAPI + Chainlit, sẵn sàng triển khai on-premise hoặc hạ tầng đám mây.

![Giao diện tổng quan](/assets/home-screen.png?raw=true "Giao diện Chainlit")

## Tổng quan điều hành

- **Mục tiêu**: rút ngắn thời gian phản hồi, chuẩn hóa câu trả lời và tận dụng dữ liệu lịch sử để cá nhân hóa trải nghiệm khách hàng Oreka.
- **Đối tượng sử dụng**: đội chăm sóc khách hàng, vận hành doanh nghiệp, hoặc đối tác muốn tích hợp chatbot tự động vào quy trình của mình.
- **Thông số chính**:
    - Python ≥ 3.9, quản lý gói bằng `uv`.
    - LLM hỗ trợ: OpenAI (mặc định), Anthropic Claude, hoặc mô hình nội bộ qua Ollama.
    - Vector store: FAISS với cache trên đĩa (`vector_store/`).
    - Khả năng mở rộng: cấu hình `prompt/` và `rag_source/` linh hoạt, tích hợp MCP để gọi dịch vụ nghiệp vụ.

## Kiến trúc & công nghệ chủ đạo

| Tầng | Công nghệ | Vai trò |
| --- | --- | --- |
| Giao diện hội thoại | [Chainlit](https://chainlit.io) | Kết xuất UI, quản lý session, widget, TTS/STT. |
| API & điều phối | [FastAPI](https://fastapi.tiangolo.com) | Phục vụ endpoint `/chat`, `/health`, lifecycle & auth. |
| Orchestration LLM | [LangChain](https://www.langchain.com) | Xây dựng pipeline RAG, contextualization, structured output. |
| Vector Store | [FAISS](https://faiss.ai) | Tìm kiếm ngữ nghĩa tốc độ cao, lưu cache embedding. |
| Nhúng & LLM | OpenAI, Anthropic, HuggingFace, Ollama | Linh hoạt lựa chọn mô hình inference & embedding. |
| Âm thanh | OpenAI Whisper, [ElevenLabs](https://elevenlabs.io) | Speech-to-Text và Text-to-Speech theo yêu cầu. |
| MCP | MCP Client + `mcp_user_server.py`, `mcp_order_server.py` | Kết nối dịch vụ hồ sơ khách hàng, đơn hàng thời gian thực. |

## Luồng tương tác RAG

1. Người dùng đăng nhập qua cơ chế `AuthManager`, Chainlit tạo session và sinh gợi ý hội thoại (starter prompts).
2. `ChatApp.create_rag()` khởi tạo đối tượng `Rag`: nạp prompt từ `prompt/`, tạo hoặc load vector store từ `rag_source/`.
3. LangChain retriever lọc 4 đoạn tri thức sát với câu hỏi, kết hợp với `chat_history` để contextualize (tùy `CONTEXTUALIZATION`).
4. MCP Client (nếu `ENABLE_MCP=true`) bổ sung dữ liệu động: hồ sơ khách hàng, dashboard đơn hàng, số dư điểm thưởng...
5. LLM sinh câu trả lời, `JsonOutputParser` xử lý cấu trúc (ví dụ follow-up question); kết quả được stream về Chainlit.
6. Nếu bật TTS, phản hồi được tổng hợp giọng nói qua ElevenLabs và phát ngay trong UI.

## Tính năng nổi bật

- Cá nhân hóa câu trả lời dựa trên user profile, lịch sử giao dịch và ngữ cảnh hội thoại.
- Truy xuất tri thức nội bộ cập nhật (PDF, Markdown, JSON) và tự lưu vector hoá.
- Hỗ trợ gợi ý follow-up thông minh, cập nhật lại tin nhắn đã gửi (editable history).
- Nhận diện giọng nói thời gian thực, phát lại phản hồi bằng giọng tự nhiên.
- Bảng điều khiển MCP: truy vấn thông tin đơn hàng, số dư, quyền hạn người dùng mà không phải huấn luyện lại mô hình.
- Khả năng tùy biến nhanh thông qua file cấu hình, script `quick_start.sh`, và hội thoại kiểu trình diễn.

## Thiết lập nhanh

Sử dụng script tự động:

```bash
chmod +x quick_start.sh
./quick_start.sh
```

Hoặc thực hiện thủ công:

```bash
uv sync
uv venv .venv
source .venv/bin/activate
cp .env.sample .env  # nếu chưa có
uv run src/main.py
```

Khi server chạy, mở trình duyệt tại [http://127.0.0.1:8000](http://127.0.0.1:8000) (FastAPI sẽ chuyển hướng tới giao diện Chainlit `/chat`).

### Triển khai bằng Docker

```bash
docker build -t chatbot-with-rag .
docker run --env-file .env -p 8000:8000 chatbot-with-rag
```

> Gợi ý: chuẩn bị sẵn file `.env` với các khóa API trước khi chạy `docker run`. Trong môi trường production, dùng trình điều phối (Kubernetes, ECS, v.v.) để quản lý biến môi trường và logging tập trung.

### Publish lên Docker Hub

```bash
# Đăng nhập Docker Hub (chỉ cần thực hiện 1 lần cho mỗi máy)
docker login

# Build và gắn tag theo định dạng <tài_khoản>/<tên_image>:<tag>
docker build -t <username>/chatbot-with-rag:latest .

# Push lên registry
docker push <username>/chatbot-with-rag:latest

# (Tuỳ chọn) deploy server thực tế
docker run --env-file .env -p 8000:8000 <username>/chatbot-with-rag:latest
```

> Lưu ý: thay `<username>` bằng tài khoản Docker Hub của bạn. Nếu muốn versioning rõ ràng, gắn thêm tag theo phiên bản app (ví dụ `:v1.0.0`) song song với `latest`.

## Cấu hình môi trường (`.env`)

| Biến | Ý nghĩa |
| --- | --- |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Dùng cho LLM & embeddings mặc định. |
| `ANTROPHIC_API_KEY`, `ANTROPHIC_MODEL` | Thay thế bằng Claude. |
| `OLLAMA_MODEL`, `HUGGINGFACE_EMBED_MODEL` | Chạy mô hình nội bộ hoặc HuggingFace embeddings. |
| `CONTEXTUALIZATION` | Bật/tắt chuẩn hoá câu hỏi dựa trên lịch sử. |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Kích hoạt TTS. |
| `ENABLE_MCP` | Điều khiển việc gọi MCP runtime. |
| `MCP_SERVERS` | Khai báo JSON các server MCP bổ sung ngoài `mcp_config.json`. |
| `VECTOR_STORE_PATH` | Thư mục lưu trữ cache FAISS. |
| `CHAINLIT_AUTH_SECRET` | Bảo vệ session Chainlit. |

> Lưu ý: chỉ cần khai báo một API key LLM để bắt đầu; các tuỳ chọn khác có thể bổ sung dần.

## Tạo RAG cho bộ dữ liệu mới

1. **Biên soạn prompt**: tạo file `.txt` trong `prompt/` (ví dụ `my_prompt.txt`) miêu tả phong cách trả lời.
2. **Chuẩn bị dữ liệu**: đặt tài liệu nguồn (PDF/Markdown/JSON/TXT) vào `rag_source/my_dataset/`.
3. **Cập nhật cấu hình**: chỉnh `ChatApp.create_rag()` trong `src/chat_app.py` trỏ tới `inputFolder="my_dataset"` và `promptFile="my_prompt.txt"`.
4. **Tái khởi động**: xoá cache cũ nếu cần (`rm -rf vector_store/my_dataset`) để forcing re-embedding, sau đó chạy lại ứng dụng.
5. **Kiểm tra**: hỏi chatbot và xác nhận log hiển thị `Loading from local store` hoặc `Saved to local store`.

LangChain sẽ tự động chunk dữ liệu (2000 ký tự, overlap 400) và lưu FAISS index vào `vector_store/<dataset>/<embedding>/`.

## Điều chỉnh trải nghiệm hội thoại

- Trong giao diện Chainlit, mở "Chat Settings" để thay đổi `Temperature`, `TopP`, bật/tắt follow-up và TTS.
- Bạn có thể bổ sung starter prompts trong `src/start.py` để phù hợp các kịch bản trình diễn.
- Cài đặt TTS cần bật `ELEVENLABS` trong `.env` và kích hoạt công tắc tương ứng.

![Cấu hình TTS](/assets/settings.png?raw=true "Cài đặt hội thoại")

## Tích hợp Model Context Protocol (MCP)

- **Cấu hình mặc định** nằm trong `mcp_config.json`, định nghĩa hai tiến trình:
    - `mcp_user_server.py`: truy vấn hồ sơ khách hàng, điểm thưởng (kết nối DB qua `lib.db_services`, `lib.order_services`).
    - `mcp_order_server.py`: thống kê đơn hàng, dự kiến giao, số tiền cần thanh toán.
- Khi `ENABLE_MCP=true`, `lib.mcp_client.MCPClient` sẽ khởi động các tiến trình này, cache kết nối theo event loop và cung cấp API tiện dụng như `get_user_order_dashboard`.
- Có thể mở rộng bằng cách:
    - Thêm server mới vào `mcp_config.json` hoặc biến môi trường `MCP_SERVERS`.
    - Triển khai server HTTP tuân thủ JSON-RPC và khai báo `url` thay vì `command`.
    - Gọi trực tiếp từ chain bằng cách sử dụng `get_mcp_client()` trong tác vụ tuỳ chỉnh.
- Để tắt MCP, đặt `ENABLE_MCP=false`; RAG sẽ fallback sang ngữ cảnh cơ bản (user ID).

## Vận hành & giám sát

- Chạy ứng dụng bằng `uv run src/main.py` hoặc `uvicorn main:create_app --factory`.
- Endpoint `/health` trả về trạng thái database thông qua `DatabaseManager.test_connection()`.
- Log MCP hiển thị trong console, giúp chẩn đoán việc khởi tạo session hoặc truy vấn đơn hàng.
- Khi dừng ứng dụng, lifecycle FastAPI sẽ đóng kết nối MCP và database tự động.

## Định hướng mở rộng gợi ý

- Bổ sung `Chainlit` task list để hiển thị KPI dịch vụ.
- Tích hợp thêm nguồn tri thức (Confluence, Notion) thông qua loader LangChain.
- Kết nối MCP với các microservice khác (ERP, CRM) để tăng chiều sâu cá nhân hóa.

## Tài nguyên tham khảo

- [Chainlit Documentation](https://docs.chainlit.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [FAISS Documentation](https://faiss.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
