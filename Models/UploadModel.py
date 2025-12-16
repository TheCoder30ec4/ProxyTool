from pydantic import BaseModel


class FileUploadRequest(BaseModel):
    filename: str
    content_type: str
    extracted_text: str
