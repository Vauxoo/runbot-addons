# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class RunbotBranch(models.Model):
    _inherit = "runbot.branch"

    @api.depends('branch_name')
    def _get_pull_head_name(self):
        """compute pull head name"""
        branches = self.filtered('repo_id.is_docker_image')
        super(RunbotBranch, self - branches)._get_pull_head_name()
        for branch in branches:
            image_name = branch.repo_id.name
            if branch.name not in image_name:
                image_name = "{0}:{1}".format(image_name, branch.name)
            branch.pull_head_name = image_name

    @api.depends('branch_name')
    def _get_branch_url(self):
        branches = self.filtered('repo_id.is_docker_image')
        return super(RunbotBranch, self - branches)._get_branch_url()

    @api.depends('name')
    def _get_branch_name(self):
        branches = self.filtered('repo_id.is_docker_image')
        super(RunbotBranch, self - branches)._get_branch_name()
        for branch in branches:
            if branch.name:
                branch.branch_name = branch.name
