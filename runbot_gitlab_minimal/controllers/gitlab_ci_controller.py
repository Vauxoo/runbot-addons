# -*- coding: utf-8 -*-
# Copyright <2017> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.addons.runbot import runbot

_logger = logging.getLogger(__name__)


class RunbotCIController(runbot.RunbotController):

    @http.route(['/runbot/hook_gitlab/<int:repo_id>',
                 '/runbot/hook_gitlab/org'], type='json', auth="public",
                website=True)
    def hook_gitlab(self, repo_id=None, **post):
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
        super(RunbotCIController, self).hook(repo_id=None, **post)
        return {}
