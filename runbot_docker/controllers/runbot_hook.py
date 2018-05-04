# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import json
import logging

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class RunbotQuayioHook(http.Controller):

    @http.route('/runbot/quayio_hook',  type='json', auth='public')
    def quayio_hook(self):
        hook_data = request.jsonrequest
        _logger.info(
            'Trigger webhook request json %s', json.dumps(hook_data, indent=2))
        repo_name = hook_data.get('repository')
        repo = request.env['runbot.repo'].sudo().search(
            [('name', '=', repo_name)])
        repo.hook_time = datetime.datetime.now().strftime(
            tools.DEFAULT_SERVER_DATETIME_FORMAT)
        return ""
