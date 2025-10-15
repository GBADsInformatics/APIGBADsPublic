from fastapi import APIRouter, Depends
from app.utils.dependencies import get_tail_adapter

router = APIRouter()

@router.get("/search")
def perform_search(query: str, tail=Depends(get_tail_adapter)):
    result = tail.perform_ner(query)
    tail.log_message(f"QUERY SENT: {query}")
    tail.log_message(f"RESULT: {result}")
    return result