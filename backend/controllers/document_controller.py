from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.core.security import CurrentUser, get_current_user
from app.schemas import Document
from services import get_document_service
from services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documentos"])


@router.post("", response_model=Document, status_code=status.HTTP_202_ACCEPTED,
             summary="Subir un archivo a la base de conocimiento")
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    doc, tmp_path = await service.receive(user, file)
    # El procesamiento (extraer, fragmentar, embeddings) corre en segundo plano.
    # El frontend consulta GET /documents hasta que el estado sea "ready" o "error".
    background.add_task(service.process, doc["id"], tmp_path, doc["filename"])
    return {**doc, "is_owner": True}


@router.get("", response_model=list[Document], summary="Listar documentos cargados")
def list_documents(
    user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    return service.list(user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un documento")
def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    service.delete(user, document_id)
