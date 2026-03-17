from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/test_page")
async def test_page():
    return {"message": "Hello World!"}
