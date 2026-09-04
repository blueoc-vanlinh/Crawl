from api.order.cage_packed_history import (
    get_packed_history_page,
    crawl_all_packed_history,
    sync_cage_history as _sync_cage_history,
    read_sheet_rows,
)


# ============================================================
# GET CAGE PACKED HISTORY
# ============================================================

def get_cage_packed_history(
    request_data=None,
    query_params=None,
):
    request_data = request_data or {}
    query_params = query_params or {}

    # Ưu tiên JSON body
    scan_time_begin = (
        request_data.get("scan_time_begin")
        or query_params.get("scan_time_begin")
    )

    scan_time_end = (
        request_data.get("scan_time_end")
        or query_params.get("scan_time_end")
    )

    page = (
        request_data.get("page")
        or request_data.get("pageno")
        or query_params.get("page")
        or query_params.get("pageno")
        or 1
    )

    count = (
        request_data.get("count")
        or query_params.get("count")
        or 100
    )

    if scan_time_begin is None:
        raise ValueError(
            "Thiếu scan_time_begin"
        )

    if scan_time_end is None:
        raise ValueError(
            "Thiếu scan_time_end"
        )

    result = get_packed_history_page(
        scan_time_begin=int(scan_time_begin),
        scan_time_end=int(scan_time_end),
        page=int(page),
        count=int(count),
    )

    return {
        "success": True,
        **result,
    }


# ============================================================
# CRAWL ALL CAGE PACKED HISTORY
# ============================================================

def get_all_cage_packed_history(
    request_data=None,
    query_params=None,
):
    request_data = request_data or {}
    query_params = query_params or {}

    scan_time_begin = (
        request_data.get("scan_time_begin")
        or query_params.get("scan_time_begin")
    )

    scan_time_end = (
        request_data.get("scan_time_end")
        or query_params.get("scan_time_end")
    )

    count = (
        request_data.get("count")
        or query_params.get("count")
        or 100
    )

    if scan_time_begin is None:
        raise ValueError(
            "Thiếu scan_time_begin"
        )

    if scan_time_end is None:
        raise ValueError(
            "Thiếu scan_time_end"
        )

    items = crawl_all_packed_history(
        scan_time_begin=int(scan_time_begin),
        scan_time_end=int(scan_time_end),
        count=int(count),
    )

    return {
        "success": True,
        "total": len(items),
        "data": items,
    }


# ============================================================
# CAGE HISTORY SYNC
# ============================================================

def sync_cage_history(
    request_data=None,
    query_params=None,
):
    request_data = request_data or {}
    query_params = query_params or {}

    scan_time_begin = (
        request_data.get("scan_time_begin")
        or query_params.get("scan_time_begin")
    )

    scan_time_end = (
        request_data.get("scan_time_end")
        or query_params.get("scan_time_end")
    )

    if scan_time_begin is None:
        raise ValueError(
            "Thiếu scan_time_begin"
        )

    if scan_time_end is None:
        raise ValueError(
            "Thiếu scan_time_end"
        )

    return {
        "success": True,
        **_sync_cage_history(
            scan_time_begin=int(scan_time_begin),
            scan_time_end=int(scan_time_end),
        ),
    }


# ============================================================
# GET CAGE HISTORY FROM GOOGLE SHEET
# ============================================================

def get_cage_history(
    query_params=None,
):
    query_params = query_params or {}

    page = (
        query_params.get(
            "page",
            1,
        )
    )

    page_size = (
        query_params.get(
            "page_size",
            query_params.get(
                "limit",
                100,
            ),
        )
    )

    search = (
        query_params.get(
            "search",
            "",
        )
    )

    result = read_sheet_rows(
        page=int(page),
        page_size=int(page_size),
        search=search,
    )

    return {
        "success": True,
        **result,
    }