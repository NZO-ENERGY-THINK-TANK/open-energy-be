import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.heat_load_vs_generation_service import (
    HeatLoadView,
    HeatLoadVsGenerationService,
)
from app.utils.date_utils import resolve_date_range

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/heat-load-vs-generation",
    tags=["Heat Load vs Electricity Generation"],
)


def _resolve_dates(
    start_date: Optional[str],
    end_date: Optional[str],
    view: HeatLoadView,
) -> tuple[datetime, datetime]:
    if start_date and end_date:
        return resolve_date_range(start_date, end_date, default_days=365)

    default_days = 365 if view == HeatLoadView.YEAR else 30
    return resolve_date_range(
        start_date,
        end_date,
        default_days=default_days,
    )


@router.get("/")
async def get_heat_load_vs_generation(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    view: HeatLoadView = Query(
        default=HeatLoadView.YEAR,
        description="Filter: month (ticks by day), year (ticks by week), custom (between dates)",
    ),
):
    """
    Delivery-3 Endpoint 7:
    Heat load vs electricity generation.
    """
    request_start = time.monotonic()

    logger.info(
        "Heat load vs generation request started: "
        "start_date=%s end_date=%s view=%s",
        start_date,
        end_date,
        view,
    )

    try:
        start_dt, end_dt = _resolve_dates(start_date, end_date, view)

        logger.info(
            "Resolved date range: start=%s end=%s view=%s",
            start_dt.isoformat(),
            end_dt.isoformat(),
            view,
        )

        result = await HeatLoadVsGenerationService.get_data(
            start_dt,
            end_dt,
            view,
        )

        logger.info(
            "Heat load vs generation request completed: "
            "duration_seconds=%.3f",
            time.monotonic() - request_start,
        )

        return result.payload

    except HTTPException as exc:
        logger.warning(
            "Heat load vs generation request failed with HTTP %s: %s",
            exc.status_code,
            exc.detail,
        )
        raise

    except Exception:
        logger.exception(
            "Heat load vs generation request failed: "
            "duration_seconds=%.3f",
            time.monotonic() - request_start,
        )
        raise HTTPException(
            status_code=424,
            detail="Failed to compute heat load vs generation",
        )


@router.get("/export")
async def export_heat_load_vs_generation(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    view: HeatLoadView = Query(
        default=HeatLoadView.YEAR,
        description="Filter: month (ticks by day), year (ticks by week), custom (between dates)",
    ),
):
    """
    Export heat load vs electricity generation to Excel.
    """
    request_start = time.monotonic()

    logger.info(
        "Heat load vs generation export started: "
        "start_date=%s end_date=%s view=%s",
        start_date,
        end_date,
        view,
    )

    try:
        start_dt, end_dt = _resolve_dates(start_date, end_date, view)

        logger.info(
            "Resolved export date range: start=%s end=%s view=%s",
            start_dt.isoformat(),
            end_dt.isoformat(),
            view,
        )

        result = await HeatLoadVsGenerationService.get_data(
            start_dt,
            end_dt,
            view,
        )

        contents = HeatLoadVsGenerationService.to_excel_bytes(result)

        filename = (
            f"heat_load_vs_generation_"
            f"{result.payload['start_date']}_to_"
            f"{result.payload['end_date']}.xlsx"
        )

        logger.info(
            "Heat load vs generation export completed: "
            "filename=%s size_bytes=%d duration_seconds=%.3f",
            filename,
            len(contents),
            time.monotonic() - request_start,
        )

        return StreamingResponse(
            iter([contents]),
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except HTTPException as exc:
        logger.warning(
            "Heat load vs generation export failed with HTTP %s: %s",
            exc.status_code,
            exc.detail,
        )
        raise

    except Exception:
        logger.exception(
            "Heat load vs generation export failed: "
            "duration_seconds=%.3f",
            time.monotonic() - request_start,
        )
        raise HTTPException(
            status_code=424,
            detail="Failed to export heat load vs generation",
        )