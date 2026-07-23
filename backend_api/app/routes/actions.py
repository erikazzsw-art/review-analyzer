from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.analysis import (
    ActionItemCreatePayload,
    ActionItemPayload,
    ActionItemsResponse,
    ActionProductGroupNotePayload,
    ActionProductGroupPayload,
    ActionProductGroupRemovePayload,
    ActionProductGroupReorderPayload,
    ActionReorderPayload,
    ActionStatusUpdatePayload,
    ActionSuggestionsUpdatePayload,
    ReviewTrackerCreatePayload,
    ReviewTrackerFromActionResponse,
    ReviewTrackerPayload,
    ReviewTrackersResponse,
    ReviewTrackerUpdatePayload,
)
from review_analyzer.action_store import (
    ACTION_STATUSES,
    create_action_item,
    get_action_item_by_id,
    get_action_items,
    remove_action_item,
    remove_product_group_actions,
    reorder_actions,
    reorder_product_groups,
    update_action_status,
    update_action_suggestions,
    update_product_group_note,
)
from review_analyzer.review_store import (
    REVIEW_TRACKER_STATUSES,
    create_review_tracker,
    get_review_tracker_by_action_id,
    get_review_trackers,
    update_review_tracker_result,
)

router = APIRouter(prefix="/actions", tags=["actions"])
trackers_router = APIRouter(prefix="/trackers", tags=["trackers"])


@router.get("", response_model=ActionItemsResponse)
def list_actions(current_user: dict = Depends(get_current_user)) -> ActionItemsResponse:
    user_id = int(current_user["id"])
    items = get_action_items(user_id)
    return ActionItemsResponse(items=[_action_payload(item) for item in items], total=len(items))


@router.post("", response_model=ActionItemPayload)
def create_action(
    payload: ActionItemCreatePayload,
    current_user: dict = Depends(get_current_user),
) -> ActionItemPayload:
    user_id = int(current_user["id"])
    action_id = create_action_item(user_id, payload.model_dump())
    action = get_action_item_by_id(user_id, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create action.")
    return _action_payload(action)


@router.patch("/product-groups/note", response_model=ActionProductGroupPayload)
def change_product_group_note(
    payload: ActionProductGroupNotePayload,
    current_user: dict = Depends(get_current_user),
) -> ActionProductGroupPayload:
    user_id = int(current_user["id"])
    if not payload.product_group_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product group key is required.")
    group = update_product_group_note(user_id, payload.product_group_key, payload.note)
    return ActionProductGroupPayload(**group)


@router.patch("/product-groups/reorder")
def change_product_group_order(
    payload: ActionProductGroupReorderPayload,
    current_user: dict = Depends(get_current_user),
) -> dict[str, int]:
    user_id = int(current_user["id"])
    updated = reorder_product_groups(user_id, payload.product_group_keys)
    return {"updated": updated}


@router.post("/product-groups/remove")
def remove_product_group(
    payload: ActionProductGroupRemovePayload,
    current_user: dict = Depends(get_current_user),
) -> dict[str, int]:
    user_id = int(current_user["id"])
    if not payload.product_group_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product group key is required.")
    removed = remove_product_group_actions(user_id, payload.product_group_key)
    if removed == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product group actions not found.")
    return {"removed": removed}


@router.patch("/reorder")
def change_action_order(
    payload: ActionReorderPayload,
    current_user: dict = Depends(get_current_user),
) -> dict[str, int]:
    user_id = int(current_user["id"])
    if not payload.product_group_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product group key is required.")
    if not payload.action_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action ids are required.")
    if not reorder_actions(user_id, payload.product_group_key, payload.action_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action order.")
    return {"updated": len(payload.action_ids)}


@router.patch("/{action_id}/status", response_model=ActionItemPayload)
def change_action_status(
    action_id: int,
    payload: ActionStatusUpdatePayload,
    current_user: dict = Depends(get_current_user),
) -> ActionItemPayload:
    user_id = int(current_user["id"])
    if payload.status not in ACTION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action status.")
    update_action_status(user_id, action_id, payload.status)
    action = get_action_item_by_id(user_id, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    return _action_payload(action)


@router.patch("/{action_id}/suggestions", response_model=ActionItemPayload)
def change_action_suggestions(
    action_id: int,
    payload: ActionSuggestionsUpdatePayload,
    current_user: dict = Depends(get_current_user),
) -> ActionItemPayload:
    user_id = int(current_user["id"])
    update_action_suggestions(user_id, action_id, payload.suggestions)
    action = get_action_item_by_id(user_id, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    return _action_payload(action)


@router.delete("/{action_id}")
def remove_action(
    action_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict[str, bool]:
    user_id = int(current_user["id"])
    if not remove_action_item(user_id, action_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    return {"removed": True}


@router.get("/{action_id}/tracker", response_model=ReviewTrackerPayload | None)
def get_action_tracker(
    action_id: int,
    current_user: dict = Depends(get_current_user),
) -> ReviewTrackerPayload | None:
    user_id = int(current_user["id"])
    tracker = get_review_tracker_by_action_id(user_id, action_id)
    return _review_tracker_payload(tracker) if tracker else None


@router.post("/{action_id}/tracker", response_model=ReviewTrackerFromActionResponse)
def create_tracker_from_action(
    action_id: int,
    payload: ReviewTrackerCreatePayload,
    current_user: dict = Depends(get_current_user),
) -> ReviewTrackerFromActionResponse:
    user_id = int(current_user["id"])
    action = get_action_item_by_id(user_id, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")

    existing_tracker = get_review_tracker_by_action_id(user_id, action_id)
    if existing_tracker:
        update_action_status(user_id, action_id, "pending_review")
        refreshed_action = get_action_item_by_id(user_id, action_id)
        if not refreshed_action:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh action.")
        return ReviewTrackerFromActionResponse(
            tracker=_review_tracker_payload(existing_tracker),
            action=_action_payload(refreshed_action),
        )

    create_review_tracker(
        user_id,
        {
            "action_item_id": action_id,
            "product_id": payload.product_id or action.get("product_id"),
            "variant_id": payload.variant_id or action.get("variant_id"),
            "tracker_title": payload.tracker_title,
            "tag_name": payload.tag_name or action.get("tag_name"),
            "baseline_pct": payload.baseline_pct if payload.baseline_pct is not None else action.get("current_pct"),
            "improvement_action": payload.improvement_action or action.get("suggested_action"),
            "effective_batch": payload.effective_batch or action.get("expected_effect_batch"),
            "review_scope": payload.review_scope or action.get("expected_review_at"),
            "current_pct": payload.current_pct,
            "result_status": payload.result_status,
            "conclusion": payload.conclusion,
        },
    )
    tracker = get_review_tracker_by_action_id(user_id, action_id)
    if not tracker:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tracker.")

    update_action_status(user_id, action_id, "pending_review")
    refreshed_action = get_action_item_by_id(user_id, action_id)
    if not refreshed_action:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh action.")
    return ReviewTrackerFromActionResponse(
        tracker=_review_tracker_payload(tracker),
        action=_action_payload(refreshed_action),
    )


@router.get("/trackers", response_model=ReviewTrackersResponse)
@trackers_router.get("", response_model=ReviewTrackersResponse)
def list_review_trackers(
    tracker_status: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> ReviewTrackersResponse:
    user_id = int(current_user["id"])
    if tracker_status is not None and tracker_status not in REVIEW_TRACKER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tracker status.")
    trackers = get_review_trackers(user_id, status=tracker_status)
    return ReviewTrackersResponse(items=[_review_tracker_payload(item) for item in trackers], total=len(trackers))


@router.patch("/trackers/{tracker_id}", response_model=ReviewTrackerPayload)
@trackers_router.patch("/{tracker_id}", response_model=ReviewTrackerPayload)
def update_review_tracker(
    tracker_id: int,
    payload: ReviewTrackerUpdatePayload,
    current_user: dict = Depends(get_current_user),
) -> ReviewTrackerPayload:
    user_id = int(current_user["id"])
    if payload.result_status not in REVIEW_TRACKER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tracker status.")
    update_review_tracker_result(
        user_id,
        tracker_id,
        {
            "review_scope": payload.review_scope,
            "current_pct": payload.current_pct,
            "result_status": payload.result_status,
            "conclusion": payload.conclusion,
        },
    )
    trackers = get_review_trackers(user_id)
    tracker = next((item for item in trackers if int(item["id"]) == tracker_id), None)
    if not tracker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracker not found.")
    return _review_tracker_payload(tracker)


def _action_payload(item: dict[str, Any]) -> ActionItemPayload:
    return ActionItemPayload(**item)


def _review_tracker_payload(item: dict[str, Any]) -> ReviewTrackerPayload:
    return ReviewTrackerPayload(**item)
