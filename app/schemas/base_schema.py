# app/schemas/base_schema.py
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder  

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    code: int
    data: Optional[T] = None

class ApiResponse:
    @staticmethod
    def success(data: Any = None, message: str = "Success", code: int = 200) -> JSONResponse:
        raw_data = data.model_dump() if hasattr(data, "model_dump") else data
        safe_data = jsonable_encoder(raw_data)
        
        response_content = {
            "success": True,
            "message": message,
            "code": code,
            "data": safe_data
        }
        return JSONResponse(status_code=code, content=response_content)

    @staticmethod
    def error(message: str = "Error", code: int = 400, data: Any = None) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "message": message,
                "code": code,
                "data": jsonable_encoder(data) 
            }
        )