import json
import logging

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class WebHook(Controller):
    @route("/fwbot_gitlab", auth="public", csrf=False, methods=["POST"], type="json")
    def fwbot_hook(self):
        data = json.loads(request.httprequest.data)
        event_type = data.get("event_type", "unknown")
        if event_type != "merge_request":
            _logger.info("Received an event of type %s, ignoring", event_type)
            return ""

        object_attributes = data.get("object_attributes", {})
        action = object_attributes.get("action", "unknown")
        if action not in ["open", "merge", "update", "reopen", "close"]:
            _logger.info("Event action is %s, ignoring", action)
            return ""

        merge_request, created = request.env["fwbot.merge.request"].sudo().gitlab_obtain_from_event(data)
        _logger.info("Processing record: %s", merge_request)
        if not created:
            merge_request.update_from_object_attributes(object_attributes)

        return ""
