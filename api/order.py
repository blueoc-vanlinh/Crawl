from core.client import FMSClient

client = FMSClient()


def pending(current_station,next_station,status):

    payload = {

        "order_status":status,

        "count":24,

        "current_station_ids":current_station,

        "next_station_ids":next_station,

        "page_no":1

    }

    return client.post(

        "/api/fleet_order/order/tracking_list/search",

        payload

    )