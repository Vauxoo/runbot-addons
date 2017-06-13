# coding: utf-8
# © 2015 Vauxoo
#   Coded by: moylop260@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests

from openerp import _, fields, models, api
from openerp.exceptions import ValidationError, Warning
from openerp.tools.misc import scan_languages


class RunbotRepo(models.Model):
    _inherit = "runbot.repo"

    is_travis2docker_build = fields.Boolean('Travis to docker build',
                                            default=True)
    use_docker_cache = fields.Boolean()
    docker_registry_server = fields.Char(
        help="Docker registry server to centralize all docker push cache "
        "images and docker pull cache images. E.g. localhost:5000. "
        "If is empty won't push it. "
        "Don't Use this feature if you use just one runbot server.")
    travis2docker_test_disable = fields.Boolean('Test Disable?')
    weblate_url = fields.Char(default="https://weblate.vauxoo.com/api")
    weblate_token = fields.Char()
    weblate_languages = fields.Char(help="List of code iso of languages E.g."
                                    " en_US,es_ES")

    @api.multi
    @api.constrains('weblate_languages')
    def _check_weblate_languages(self):
        supported_langs = [item[0] for item in scan_languages()]
        supported_langs.extend(set([lang.split('_')[0] for lang in
                                    supported_langs]))
        for record in self.filtered('weblate_languages'):
            langs = record.weblate_languages.split(',')
            for lang in langs:
                lang = lang.strip()
                if lang not in supported_langs:
                    raise ValidationError(_("The language '%s' is not"
                                            "supported" % lang))

    @api.multi
    def weblate_validation(self):
        for record in self:
            if not record.weblate_url or not record.weblate_token:
                return
            session = requests.Session()
            session.headers.update({
                'Accept': 'application/json',
                'User-Agent': 'mqt',
                'Authorization': 'Token %s' % record.weblate_token
            })
            response = session.get(record.weblate_url)
            response.raise_for_status()
            json = response.json()
            if 'projects' not in json:
                raise ValidationError(_('Response json bad formated'))
        raise Warning(_('Connection with weblate successful'))

    @api.multi
    def cron_weblate(self):
        self.ensure_one()
        if not self.weblate_url or not self.weblate_token:
            return
        branch_ids = self.env['runbot.branch'].search([
            ['repo_id', '=', self.id], ['uses_weblate', '=', True]])
        for branch in branch_ids:
            branch.cron_weblate()
