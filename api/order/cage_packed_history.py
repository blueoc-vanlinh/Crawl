import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import BASE_URL, get_headers


SPREADSHEET_ID = (
    "1YfRPJd99ipWnUqPqXCFDlQzHj8ADxdP_UE1363KqLS8"
)

SHEET_GID = 1243544479

PACKED_HISTORY_URL = (
    f"{BASE_URL}"
    "/api/in-station/cage/packed_history/list"
)

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

SERVICE_ACCOUNT_FILE = (
    BASE_DIR
    / "service_account.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

VN_TZ = timezone(
    timedelta(
        hours=7
    )
)

TIME_FIELDS = {
    "mapping_item_scan_time",
    "cage_packed_time",
    "cage_packing_start_time",
    "ctime",
    "mtime",
    "detach_time",
    "create_time",
    "update_time",
    "completed_time",
}


def get_google_service():
    credentials = (
        service_account
        .Credentials
        .from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


def get_sheet_name_by_gid(
    service,
):
    spreadsheet = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            fields=
                "sheets.properties(sheetId,title)",
        )
        .execute()
    )

    for sheet in spreadsheet.get(
        "sheets",
        [],
    ):
        properties = (
            sheet.get(
                "properties",
                {},
            )
        )

        sheet_id = (
            properties.get(
                "sheetId",
                -1,
            )
        )

        if int(
            sheet_id
        ) == int(
            SHEET_GID
        ):
            return (
                properties.get(
                    "title"
                )
            )

    raise RuntimeError(
        f"Không tìm thấy sheet gid={SHEET_GID}"
    )


def format_timestamp(
    value,
):
    if value in (
        None,
        "",
        0,
        "0",
    ):
        return ""

    if isinstance(
        value,
        str,
    ):
        value = (
            value.strip()
        )

        if not value:
            return ""

        if "/" in value:
            return value

    try:
        timestamp = float(
            value
        )

        if (
            timestamp >
            10_000_000_000
        ):
            timestamp /= 1000

        if (
            timestamp <
            946684800
        ):
            return str(
                value
            )

        dt = (
            datetime
            .fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )
            .astimezone(
                VN_TZ
            )
        )

        return dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
        OSError,
    ):
        return str(
            value
        )


def normalize_cell(
    value,
):
    if value is None:
        return ""

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )

    return value


def convert_item_times(
    item,
):
    result = {}

    for (
        key,
        value,
    ) in item.items():
        if key in TIME_FIELDS:
            result[
                key
            ] = (
                format_timestamp(
                    value
                )
            )
        else:
            result[
                key
            ] = (
                normalize_cell(
                    value
                )
            )

    return result


def get_packed_history_page(
    scan_time_begin,
    scan_time_end,
    page=1,
    count=100,
):
    payload = {
        "pageno":
            int(
                page
            ),

        "count":
            int(
                count
            ),

        "scan_time_begin":
            int(
                scan_time_begin
            ),

        "scan_time_end":
            int(
                scan_time_end
            ),
    }

    response = (
        requests.post(
            PACKED_HISTORY_URL,
            headers=
                get_headers(),
            json=
                payload,
            timeout=
                60,
        )
    )

    response.raise_for_status()

    result = (
        response.json()
    )

    retcode = (
        result.get(
            "retcode"
        )
    )

    if retcode not in (
        0,
        "0",
        None,
    ):
        raise RuntimeError(
            f"SPX retcode={retcode}: "
            f"{result.get('message', '')}"
        )

    data = (
        result.get(
            "data",
            {},
        )
    )

    if not isinstance(
        data,
        dict,
    ):
        data = {}

    items = (
        data.get(
            "list",
            [],
        )
    )

    if not isinstance(
        items,
        list,
    ):
        items = []

    return {
        "total":
            int(
                data.get(
                    "total",
                    0,
                )
                or 0
            ),

        "pageno":
            int(
                data.get(
                    "pageno",
                    page,
                )
                or page
            ),

        "count":
            int(
                data.get(
                    "count",
                    count,
                )
                or count
            ),

        "list":
            items,
    }


def crawl_all_packed_history(
    scan_time_begin,
    scan_time_end,
    count=100,
):
    first = (
        get_packed_history_page(
            scan_time_begin=
                scan_time_begin,
            scan_time_end=
                scan_time_end,
            page=
                1,
            count=
                count,
        )
    )

    total = (
        first.get(
            "total",
            0,
        )
    )

    all_items = list(
        first.get(
            "list",
            [],
        )
    )

    print(
        f"CAGE TOTAL: {total}"
    )

    print(
        f"CAGE PAGE 1: "
        f"{len(all_items)}/{total}"
    )

    if (
        total <=
        len(all_items)
    ):
        return all_items

    total_pages = max(
        1,
        math.ceil(
            total / count
        ),
    )

    for page in range(
        2,
        total_pages + 1,
    ):
        result = (
            get_packed_history_page(
                scan_time_begin=
                    scan_time_begin,
                scan_time_end=
                    scan_time_end,
                page=
                    page,
                count=
                    count,
            )
        )

        page_items = (
            result.get(
                "list",
                [],
            )
        )

        if not page_items:
            print(
                f"CAGE PAGE {page}: EMPTY"
            )
            break

        all_items.extend(
            page_items
        )

        print(
            f"CAGE PAGE {page}: "
            f"{len(all_items)}/{total}"
        )

        time.sleep(
            0.05
        )

    return all_items


def build_key(
    item,
):
    shipment = (
        str(
            item.get(
                "mapping_item_number",
                "",
            )
        )
        .strip()
        .upper()
    )

    scan_time = (
        str(
            item.get(
                "mapping_item_scan_time",
                "",
            )
        )
        .strip()
    )

    cage_id = (
        str(
            item.get(
                "cage_id",
                "",
            )
        )
        .strip()
        .upper()
    )

    return (
        f"{shipment}|"
        f"{scan_time}|"
        f"{cage_id}"
    )


def prepare_rows(
    items,
):
    rows = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        row = {
            "_key":
                build_key(
                    item
                )
        }

        converted = (
            convert_item_times(
                item
            )
        )

        row.update(
            converted
        )

        rows.append(
            row
        )

    return rows


def column_letter(
    number,
):
    result = ""

    while number:
        (
            number,
            remainder,
        ) = divmod(
            number - 1,
            26,
        )

        result = (
            chr(
                65 + remainder
            )
            + result
        )

    return result


def save_rows_to_sheet(
    rows,
):
    service = (
        get_google_service()
    )

    sheet_name = (
        get_sheet_name_by_gid(
            service
        )
    )

    values_api = (
        service
        .spreadsheets()
        .values()
    )

    if not rows:
        values_api.clear(
            spreadsheetId=
                SPREADSHEET_ID,
            range=
                f"'{sheet_name}'!A:ZZ",
            body={},
        ).execute()

        return {
            "inserted":
                0,
            "updated":
                0,
            "total_sheet":
                0,
        }

    headers = [
        "_key",
    ]

    for row in rows:
        for key in row.keys():
            if (
                key not in
                headers
            ):
                headers.append(
                    key
                )

    final_values = [
        headers
    ]

    for row in rows:
        final_values.append(
            [
                row.get(
                    header,
                    "",
                )
                for header
                in headers
            ]
        )

    print(
        "CAGE SAMPLE BEFORE WRITE:"
    )

    if len(
        final_values
    ) > 1:
        sample = (
            final_values[
                1
            ]
        )

        for field in (
            "mapping_item_scan_time",
            "cage_packed_time",
            "cage_packing_start_time",
            "ctime",
            "mtime",
            "detach_time",
        ):
            if field not in headers:
                continue

            index = (
                headers.index(
                    field
                )
            )

            print(
                field,
                "=",
                sample[
                    index
                ],
            )

    values_api.clear(
        spreadsheetId=
            SPREADSHEET_ID,
        range=
            f"'{sheet_name}'!A:ZZ",
        body={},
    ).execute()

    end_col = (
        column_letter(
            len(
                headers
            )
        )
    )

    values_api.update(
        spreadsheetId=
            SPREADSHEET_ID,
        range=(
            f"'{sheet_name}'!"
            f"A1:{end_col}"
            f"{len(final_values)}"
        ),
        valueInputOption=
            "RAW",
        body={
            "values":
                final_values
        },
    ).execute()

    print(
        "CAGE SHEET SAVED:"
    )

    print(
        f"TOTAL SHEET: "
        f"{len(rows)}"
    )

    return {
        "inserted":
            len(
                rows
            ),
        "updated":
            0,
        "total_sheet":
            len(
                rows
            ),
    }


def read_sheet_rows(
    page=1,
    page_size=100,
    search="",
):
    service = (
        get_google_service()
    )

    sheet_name = (
        get_sheet_name_by_gid(
            service
        )
    )

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=
                SPREADSHEET_ID,
            range=
                f"'{sheet_name}'!A:ZZ",
        )
        .execute()
    )

    values = (
        result.get(
            "values",
            [],
        )
    )

    page = max(
        1,
        int(
            page
        ),
    )

    page_size = max(
        1,
        min(
            int(
                page_size
            ),
            500,
        ),
    )

    if not values:
        return {
            "total":
                0,
            "page":
                page,
            "page_size":
                page_size,
            "total_pages":
                0,
            "data":
                [],
        }

    headers = [
        str(
            value
        ).strip()
        for value
        in values[0]
    ]

    rows = []

    keyword = (
        str(
            search
            or ""
        )
        .strip()
        .upper()
    )

    for values_row in (
        values[
            1:
        ]
    ):
        row = {}

        for (
            index,
            header,
        ) in enumerate(
            headers
        ):
            if not header:
                continue

            row[
                header
            ] = (
                values_row[
                    index
                ]
                if index <
                len(
                    values_row
                )
                else ""
            )

        if not any(
            str(
                value
            ).strip()
            for value
            in row.values()
        ):
            continue

        if keyword:
            searchable = (
                " ".join(
                    [
                        str(
                            row.get(
                                "mapping_item_number",
                                "",
                            )
                        ),
                        str(
                            row.get(
                                "cage_id",
                                "",
                            )
                        ),
                        str(
                            row.get(
                                "cage_name",
                                "",
                            )
                        ),
                        str(
                            row.get(
                                "operator",
                                "",
                            )
                        ),
                        str(
                            row.get(
                                "station_id",
                                "",
                            )
                        ),
                    ]
                )
                .upper()
            )

            if (
                keyword not in
                searchable
            ):
                continue

        rows.append(
            row
        )

    total = (
        len(
            rows
        )
    )

    total_pages = (
        math.ceil(
            total /
            page_size
        )
        if total
        else 0
    )

    if (
        total_pages
        and
        page > total_pages
    ):
        page = (
            total_pages
        )

    start = (
        page - 1
    ) * page_size

    end = (
        start
        + page_size
    )

    page_rows = (
        rows[
            start:end
        ]
    )

    return {
        "total":
            total,
        "page":
            page,
        "page_size":
            page_size,
        "total_pages":
            total_pages,
        "data":
            page_rows,
    }


def sync_cage_history(
    scan_time_begin,
    scan_time_end,
):
    print(
        "CAGE SYNC RANGE:"
    )

    print(
        "BEGIN:",
        format_timestamp(
            scan_time_begin
        ),
        scan_time_begin,
    )

    print(
        "END:",
        format_timestamp(
            scan_time_end
        ),
        scan_time_end,
    )

    items = (
        crawl_all_packed_history(
            scan_time_begin=
                scan_time_begin,
            scan_time_end=
                scan_time_end,
            count=
                100,
        )
    )

    rows = (
        prepare_rows(
            items
        )
    )

    print(
        f"CAGE PREPARED: "
        f"{len(rows)}"
    )

    if rows:
        sample = (
            rows[0]
        )

        print(
            "CAGE CONVERTED SAMPLE:"
        )

        print(
            "SHIPMENT:",
            sample.get(
                "mapping_item_number"
            ),
        )

        print(
            "SCAN:",
            sample.get(
                "mapping_item_scan_time"
            ),
        )

        print(
            "PACKING START:",
            sample.get(
                "cage_packing_start_time"
            ),
        )

        print(
            "PACKED:",
            sample.get(
                "cage_packed_time"
            ),
        )

        print(
            "DETACH:",
            sample.get(
                "detach_time"
            ),
        )

    sheet_result = (
        save_rows_to_sheet(
            rows
        )
    )

    return {
        "api_total":
            len(
                items
            ),
        "inserted":
            sheet_result[
                "inserted"
            ],
        "updated":
            sheet_result[
                "updated"
            ],
        "total_sheet":
            sheet_result[
                "total_sheet"
            ],
    }