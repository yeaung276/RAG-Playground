from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response

from app.backgrounds.evaluation_processor import EvaluationProcessor
from app.dependencies.services import (
    get_evaluation_processor,
    get_experimentation_service,
)
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentPage,
    ExperimentRead,
    ExperimentScores,
)
from app.services.dataset.experiment_service import ExperimentationService

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentRead, status_code=201)
async def create_experiment(
    payload: ExperimentCreate,
    background_tasks: BackgroundTasks,
    svc: ExperimentationService = Depends(get_experimentation_service),
    processor: EvaluationProcessor = Depends(get_evaluation_processor),
):
    experiment = await svc.create(payload)
    background_tasks.add_task(processor.run, experiment.id)
    return experiment


@router.get("", response_model=ExperimentPage)
async def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    dataset_id: str | None = Query(None, alias="datasetId"),
    svc: ExperimentationService = Depends(get_experimentation_service),
):
    return await svc.list(page=page, page_size=page_size, dataset_id=dataset_id)


@router.get("/score_board", response_model=list[ExperimentScores])
async def get_score_board(
    dataset_id: str = Query(alias="datasetId"),
    svc: ExperimentationService = Depends(get_experimentation_service),
):
    return await svc.score_board(dataset_id)


@router.get("/{experiment_id}", response_model=ExperimentRead)
async def get_experiment(
    experiment_id: str,
    svc: ExperimentationService = Depends(get_experimentation_service),
):
    return await svc.get(experiment_id)


@router.post("/{experiment_id}/rerun", response_model=ExperimentRead)
async def rerun_experiment(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    svc: ExperimentationService = Depends(get_experimentation_service),
    processor: EvaluationProcessor = Depends(get_evaluation_processor),
):
    experiment = await svc.clear_result(experiment_id)
    background_tasks.add_task(processor.run, experiment.id, skip_indexing=True)
    return experiment


@router.get("/{experiment_id}/best", response_model=dict[str, float])
async def get_best_scores(
    experiment_id: str,
    svc: ExperimentationService = Depends(get_experimentation_service),
):
    return await svc.best_scores(experiment_id)


@router.get("/{experiment_id}/result")
async def get_experiment_result(
    experiment_id: str,
    svc: ExperimentationService = Depends(get_experimentation_service),
):
    name, data = await svc.read_result(experiment_id)
    disposition = f"attachment; filename*=UTF-8''{quote(name)}"
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": disposition},
    )
