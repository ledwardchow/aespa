"""Benchmark Lab APIs for evaluating completed ordinary SAST runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session, select

from aespa.db import get_session
from aespa.models import (
    BenchmarkComparison,
    BenchmarkDataset,
    BenchmarkEvaluation,
    BenchmarkMatch,
)
from aespa.schemas import (
    BenchmarkComparisonIn,
    BenchmarkComparisonOut,
    BenchmarkDatasetIn,
    BenchmarkDatasetOut,
    BenchmarkEvaluationIn,
    BenchmarkEvaluationOut,
    BenchmarkMatchOut,
    BenchmarkMatchReviewIn,
)
from aespa.services import benchmark_lab as service

router = APIRouter(prefix="/api/benchmark-lab", tags=["benchmark-lab"])


@router.get("/comparisons", response_model=list[BenchmarkComparisonOut])
def list_comparisons(
    session: Session = Depends(get_session),
) -> list[BenchmarkComparisonOut]:
    rows = session.exec(
        select(BenchmarkComparison).order_by(BenchmarkComparison.id.desc())
    ).all()
    return [service.comparison_out(session, row) for row in rows]


@router.post("/comparisons", response_model=BenchmarkComparisonOut, status_code=201)
def create_comparison(
    payload: BenchmarkComparisonIn, session: Session = Depends(get_session)
) -> BenchmarkComparisonOut:
    try:
        return service.comparison_out(
            session, service.create_comparison(session, payload)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/comparisons/{comparison_id}", response_model=BenchmarkComparisonOut)
def get_comparison(
    comparison_id: int, session: Session = Depends(get_session)
) -> BenchmarkComparisonOut:
    row = session.get(BenchmarkComparison, comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Benchmark comparison not found")
    return service.comparison_out(session, row)


@router.post(
    "/comparisons/{comparison_id}/recalculate", response_model=BenchmarkComparisonOut
)
def recalculate_comparison(
    comparison_id: int, session: Session = Depends(get_session)
) -> BenchmarkComparisonOut:
    row = session.get(BenchmarkComparison, comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Benchmark comparison not found")
    return service.comparison_out(session, service.recalculate_comparison(session, row))


def _dataset_or_404(session: Session, dataset_id: int) -> BenchmarkDataset:
    dataset = session.get(BenchmarkDataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Benchmark dataset not found")
    return dataset


def _evaluation_or_404(session: Session, evaluation_id: int) -> BenchmarkEvaluation:
    evaluation = session.get(BenchmarkEvaluation, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Benchmark evaluation not found")
    return evaluation


@router.get("/datasets", response_model=list[BenchmarkDatasetOut])
def list_datasets(session: Session = Depends(get_session)) -> list[BenchmarkDatasetOut]:
    return [service.dataset_out(row) for row in service.list_datasets(session)]


@router.post("/datasets", response_model=BenchmarkDatasetOut, status_code=201)
def create_dataset(
    payload: BenchmarkDatasetIn, session: Session = Depends(get_session)
) -> BenchmarkDatasetOut:
    try:
        return service.dataset_out(service.create_dataset(session, payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/datasets/{dataset_id}", response_model=BenchmarkDatasetOut)
def get_dataset(
    dataset_id: int, session: Session = Depends(get_session)
) -> BenchmarkDatasetOut:
    return service.dataset_out(_dataset_or_404(session, dataset_id))


@router.put("/datasets/{dataset_id}", response_model=BenchmarkDatasetOut)
def update_dataset(
    dataset_id: int,
    payload: BenchmarkDatasetIn,
    session: Session = Depends(get_session),
) -> BenchmarkDatasetOut:
    dataset = _dataset_or_404(session, dataset_id)
    try:
        return service.dataset_out(service.update_dataset(session, dataset, payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, session: Session = Depends(get_session)) -> None:
    dataset = _dataset_or_404(session, dataset_id)
    if (
        session.exec(
            select(BenchmarkEvaluation).where(
                BenchmarkEvaluation.dataset_id == dataset_id
            )
        ).first()
        is not None
    ):
        raise HTTPException(
            status_code=409, detail="Dataset is referenced by an evaluation"
        )
    session.delete(dataset)
    session.commit()


@router.get("/evaluations", response_model=list[BenchmarkEvaluationOut])
def list_evaluations(
    session: Session = Depends(get_session),
) -> list[BenchmarkEvaluationOut]:
    evaluations = session.exec(
        select(BenchmarkEvaluation).order_by(BenchmarkEvaluation.id.desc())
    ).all()
    return [service.evaluation_out(session, evaluation) for evaluation in evaluations]


@router.post("/evaluations", response_model=BenchmarkEvaluationOut, status_code=201)
def create_evaluation(
    payload: BenchmarkEvaluationIn, session: Session = Depends(get_session)
) -> BenchmarkEvaluationOut:
    try:
        evaluation = service.create_evaluation(session, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return service.evaluation_out(session, evaluation)


@router.get("/evaluations/{evaluation_id}", response_model=BenchmarkEvaluationOut)
def get_evaluation(
    evaluation_id: int, session: Session = Depends(get_session)
) -> BenchmarkEvaluationOut:
    return service.evaluation_out(session, _evaluation_or_404(session, evaluation_id))


@router.post("/evaluations/{evaluation_id}/run", response_model=BenchmarkEvaluationOut)
async def run_evaluation(
    evaluation_id: int, session: Session = Depends(get_session)
) -> BenchmarkEvaluationOut:
    evaluation = _evaluation_or_404(session, evaluation_id)
    try:
        return service.evaluation_out(
            session, await service.run_evaluation(session, evaluation)
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/evaluations/{evaluation_id}/matches/{match_id}/review",
    response_model=BenchmarkMatchOut,
)
def review_match(
    evaluation_id: int,
    match_id: int,
    payload: BenchmarkMatchReviewIn,
    session: Session = Depends(get_session),
) -> BenchmarkMatchOut:
    _evaluation_or_404(session, evaluation_id)
    match = session.get(BenchmarkMatch, match_id)
    if match is None or match.evaluation_id != evaluation_id:
        raise HTTPException(status_code=404, detail="Benchmark match not found")
    try:
        return BenchmarkMatchOut.model_validate(
            service.review_match(session, match, payload)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/evaluations/{evaluation_id}/export")
def export_evaluation(
    evaluation_id: int,
    format: str = Query(default="json", pattern="^(json|csv|markdown)$"),
    session: Session = Depends(get_session),
) -> Response:
    evaluation = _evaluation_or_404(session, evaluation_id)
    body, media_type, filename = service.export_evaluation(session, evaluation, format)
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
