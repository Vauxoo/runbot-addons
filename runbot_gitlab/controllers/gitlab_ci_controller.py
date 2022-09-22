# Copyright <2017> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.addons.runbot.controllers.hook import RunbotHook
from odoo.http import request

_logger = logging.getLogger(__name__)


class RunbotCIController(RunbotHook):

    @http.route(
        ['/runbot/hook_gitlab/<int:repo_id>', '/runbot/hook_gitlab/org'],
        type='json', auth="public", website=True, csrf=False)
    def hook_gitlab(self, repo_id=None, **post):
        if repo_id:
            return self.hook(repo_id, **post)
        data = request.jsonrequest
        event = data.get('object_kind')
        if event in ['push', 'merge_request', 'build']:
            # Compatible with gitlab version >=8.5 and <8.5
            project = data.get('project') or data.get('repository')
            ssh_url = project.get('git_ssh_url') or project.get('ssh_url')
            http_url = project.get('git_http_url') or project.get('http_url')
            if event == "build":
                # The "jobs" webhook only are triggered from from dev projects
                # but we need to match with stable one
                ssh_url = ssh_url.replace("-dev/", "/")
                http_url = http_url.replace("-dev/", "/")
            repo_domain = ['|', '|', ('name', '=', ssh_url),
                           ('name', '=', http_url),
                           ('name', '=', http_url.rstrip('.git'))]
            repo = request.env['runbot.repo'].sudo().search(repo_domain,
                                                            limit=1)
            if repo and event != 'build':
                return self.hook(repo.id, **post)
            if (event == "build" and data["build_name"] in ("build_deployv", "build_docker") and
                data["build_status"] == "success" and repo and repo.is_t2d_deployv):
                build_domain = [("repo_id", "=", repo.id), ("name", "=", data["sha"])]
                build = request.env["runbot.build"].sudo().search(build_domain, order='id DESC', limit=1)
                if build:
                    build.write({"deployv_image_built": True})
                    forced_builds = build._force("Image built so rebuild runbot job")
                    if forced_builds:
                        forced_builds.write({"deployv_image_built": True})
        return ""
