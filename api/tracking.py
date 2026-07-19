from core.client import FMSClient

client = FMSClient()


def tracking(shipment):

    return client.get(

        "/api/xxxx/tracking_info",

        {

            "shipment_id": shipment

        }

    )