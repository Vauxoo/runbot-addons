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
            repo_domain = ['|', '|', ('name', '=', ssh_url),
                           ('name', '=', http_url),
                           ('name', '=', http_url.rstrip('.git')),
                           ]
            repo = request.env['runbot.repo'].sudo().search(repo_domain, limit=1)
            if repo and event != 'build':
                return self.hook(repo.id, **post)
            if (event == "build" and data["build_name"] in ("build_deployv", "build_docker") and
                data["build_status"] == "success"):
                # The "jobs" webhook only are triggered from from dev projects
                # but we need to match with stable one
                ssh_url_stb = ssh_url.replace("-dev", "/")
                http_url_stb = http_url.replace("-dev", "/")
                repo_domain = [
                    '|', '|', ('name', '=', ssh_url_stb),
                    ('name', '=', http_url_stb),
                    ('name', '=', http_url_stb.rstrip('.git')),
                ]
                repo |= request.env['runbot.repo'].sudo().search(repo_domain, limit=1)
                repo = repo.filtered("is_t2d_deployv")
                if not repo:
                    return ""
                build = request.env["runbot.build"].sudo()
                query = """SELECT id FROM runbot_build WHERE id IN (
                    SELECT MAX(id) AS build_id
                    FROM runbot_build
                    WHERE repo_id IN %s
                      AND name = %s
                    GROUP BY branch_id)
                AND state='done' AND result='skipped' AND deployv_image_built IS NOT TRUE
                """
                request.env.cr.execute(query, (tuple(repo.ids), data["sha"]))
                builds_waiting_image_ids = [i[0] for i in request.env.cr.fetchall()]
                if not builds_waiting_image_ids:
                    _logger.info("Build of repo_ids=%s and sha=%s are not waiting for image built", repo.ids, data["sha"])
                    return
                builds_waiting_image = build.browse(builds_waiting_image_ids)
                msg = "Image built so rebuild runbot job"
                builds_waiting_image.write({"deployv_image_built": True})
                builds_waiting_image._logger(msg)
                for build2force in builds_waiting_image:
                    forced_build = build2force._force(msg)
                    if forced_build and forced_build != build2force:
                        forced_build.write({"deployv_image_built": True})
                        forced_build._logger(msg)
        return ""
