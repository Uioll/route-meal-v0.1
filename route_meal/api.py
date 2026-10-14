from fastapi import FastAPI


app = FastAPI(
    title="顺路去哪吃 API",
    description="为微信小程序提供餐厅筛选和抽签服务",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "message": "欢迎使用顺路去哪吃 API",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
    }