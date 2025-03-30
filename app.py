from fastapi import FastAPI
from database import Base, engine
from controllers import game_controller  # file controller của bạn

# Khởi tạo FastAPI app
app = FastAPI(
    title="Quorinov Game Backend",
    description="API cho game Quorinov",
    version="1.0.0"
)

# Tạo bảng trong database nếu chưa có
Base.metadata.create_all(bind=engine)

# Đăng ký các router
app.include_router(game_controller.router, prefix="/game", tags=["Game"])

# (Tùy chọn) route kiểm tra hoạt động
@app.get
