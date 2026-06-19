from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from sport_vision.db.database import get_db
from sport_vision.report.schemas import ReportGenerateRequest, ReportResponse
from sport_vision.report.services import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_session_report(req: ReportGenerateRequest, db: Session = Depends(get_db)):
    """为指定训练会话分析评估生成大模型战术教练指导报告"""
    db_report = ReportService.generate_coaching_report(db, req.session_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="训练会话不存在")
    return db_report


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """查询指定指导报告"""
    db_report = ReportService.get_report(db, report_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return db_report


@router.get("/session/{session_id}", response_model=list[ReportResponse])
def get_session_reports(session_id: int, db: Session = Depends(get_db)):
    """获取会话绑定的所有评估报告记录"""
    return ReportService.get_session_reports(db, session_id)


@router.get("/{report_id}/export")
def export_report_file(report_id: int, db: Session = Depends(get_db)):
    """导出报告文件，返回 Markdown 纯文本附件下载"""
    db_report = ReportService.get_report(db, report_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="报告不存在")

    filename = f"basketball_coaching_report_{report_id}.md"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    return Response(content=db_report.report_text, media_type="text/markdown", headers=headers)
