from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import shutil
import re
import hashlib
from loguru import logger

from backend.models import get_db
from backend.models.db_models import Document as DBDocument
from backend.models.schemas import DocumentResponse, DocumentCreate
from backend.core.document_loader import DocumentLoader
from backend.core.vector_store import VectorStore
from backend.config import settings

router = APIRouter()


def generate_collection_name(filename: str) -> str:
    """
    生成合法的Milvus集合名称
    Milvus要求：只能包含数字、字母和下划线
    
    Args:
        filename: 原始文件名
        
    Returns:
        合法的集合名称
    """
    # 移除文件扩展名
    name = Path(filename).stem
    
    # 只保留字母、数字和下划线，其他字符替换为下划线
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # 如果名称为空或只有下划线，使用哈希值
    if not safe_name or safe_name.replace('_', '') == '':
        safe_name = hashlib.md5(filename.encode()).hexdigest()[:16]
    
    # 如果名称以数字开头，添加前缀
    if safe_name[0].isdigit():
        safe_name = 'col_' + safe_name
    
    # 限制长度（Milvus建议不超过255字符）
    if len(safe_name) > 200:
        # 保留前100个字符，加上哈希值确保唯一性
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:12]
        safe_name = safe_name[:100] + '_' + hash_suffix
    
    # 添加前缀避免与系统集合冲突
    collection_name = f"doc_{safe_name}"
    
    return collection_name


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传文档"""
    try:
        # 检查文件类型
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}"
            )
        
        # 保存文件
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # 生成合法的集合名称
        collection_name = generate_collection_name(file.filename)
        
        # 创建数据库记录
        db_doc = DBDocument(
            filename=file.filename,
            file_type=file_ext,
            file_path=str(file_path),
            file_size=file_size,
            vector_collection=collection_name
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # 加载和处理文档
        loader = DocumentLoader()
        document = loader.load(str(file_path))
        chunks = loader.chunk(
            document,
            chunk_size=settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=settings.DEFAULT_CHUNK_OVERLAP
        )
        
        # 添加文档ID到chunk metadata
        for chunk in chunks:
            chunk.metadata["doc_id"] = str(db_doc.id)
        
        # 存储到向量库
        vector_store = VectorStore(db_doc.vector_collection)
        chunk_count = vector_store.add_documents(chunks)
        
        # 更新块数量
        db_doc.chunk_count = chunk_count
        db.commit()
        db.refresh(db_doc)
        
        logger.info(f"文档上传成功: {file.filename}, ID: {db_doc.id}")
        
        return db_doc
        
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    documents = db.query(DBDocument).offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档详情"""
    document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """删除文档"""
    document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 删除向量库中的数据
        if document.vector_collection:
            try:
                vector_store = VectorStore(document.vector_collection)
                vector_store.drop_collection()
                logger.info(f"向量库集合删除成功: {document.vector_collection}")
            except Exception as vec_error:
                # 如果向量库删除失败（可能collection不存在或名称非法），记录日志但继续删除
                logger.warning(f"向量库集合删除失败（可能不存在或名称非法）: {vec_error}")
        
        # 删除文件
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"文件删除成功: {file_path}")
        
        # 删除数据库记录
        db.delete(document)
        db.commit()
        
        logger.info(f"文档删除成功: {document.filename}, ID: {document_id}")
        return {"message": "文档删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档删除失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

