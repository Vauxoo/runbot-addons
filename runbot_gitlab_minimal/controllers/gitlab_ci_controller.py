# -*- coding: utf-8 -*-
# Copyright <2017> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import pprint
import logging

import openerp
from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class RunbotCIController(http.Controller):

    @http.route(['/runbot/hook_gitlab/<int:repo_id>',
                 '/runbot/hook_gitlab/org'], type='json', auth="public",
                website=True)
    def hook(self, repo_id=None, **post):
        data = request.jsonrequest
        event = data['object_kind'] if data.has_key('object_kind') else None
        repository = data['repository']
        if repo_id is None:
            if event in ['push', 'merge_request']:
                repo_domain = ['|', ('name', '=', repository['url']),
                               '|',
                               ('name', '=', repository['homepage']),
                               ('name', '=', repository['homepage'] + '.git')]
                repo = request.registry['runbot.repo'].search(request.cr,
                                                              SUPERUSER_ID,
                                                              repo_domain,
                                                              limit=1)
                repo_id = repo[0] if len(repo) else None
        if repo_id:
            repo = request.registry['runbot.repo'].browse(request.cr,
                                                          SUPERUSER_ID,
                                                          [repo_id])
            repo.hook_time = datetime.datetime.now().strftime(
                openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            _logger.debug('Repo not found from request data: %s',
                          pprint.pformat(request.jsonrequest)[:450])
        return {}
