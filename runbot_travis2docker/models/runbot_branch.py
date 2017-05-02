# coding: utf-8
# © 2015 Vauxoo
#   Coded by: moylop260@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime
import requests

from urlparse import urlparse

from openerp import fields, models, api


class RunbotBranch(models.Model):
    _inherit = "runbot.branch"

    uses_weblate = fields.Boolean(help='Synchronize with Weblate')
    updated_weblate = fields.Datetime(help='Last update of weblate')

    @api.model
    def cron_weblate(self):
        for branch in self.search([('uses_weblate', '=', True)]):
            if (not branch.repo_id.weblate_token or
                    not branch.repo_id.weblate_url):
                continue
            current_date = (datetime.strptime(branch.updated_weblate,
                                              '%Y-%m-%d %H:%M:%S')
                            if branch.updated_weblate
                            else None)
            new_date = None
            url = branch.repo_id.weblate_url
            session = requests.Session()
            session.headers.update({
                'Accept': 'application/json',
                'User-Agent': 'runbot_travis2docker',
                'Authorization': 'Token %s' % branch.repo_id.weblate_token
            })
            projects = session.get(url + '/projects/').json()
            for project in projects['results']:
                components = session.get('%s/projects/%s/components'
                                         % (url, project['slug'])).json()
                for component in components['results']:
                    slug = branch.repo_id.name
                    repo = branch.repo_id.name
                    if '@' in repo:
                        slug = repo.split('@')[1:].pop().replace('/', '-')
                    if (any([pre for pre in ['http://', 'https://']
                             if pre in repo])):
                        slug = repo.replace(
                            'https://', '').replace('http://', '').split('/')
                        slug = slug[0] + ':' +  slug[1] + '-' + slug[2]
                    slug = (slug.replace('.git', '') +
                            '(' + component['branch'] + ')')
                    if project['name'] != slug:
                        continue
                    changes = session.get('%s/components/%s/%s/changes/'
                                          % (url, project['slug'],
                                             component['slug'])).json()
                    if not changes['results']:
                        continue
                    change = changes['results'].pop()
                    date = datetime.strptime(
                        change['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    new_date = (date
                                if (not new_date or date > new_date)
                                else new_date)
            if ((current_date and new_date and
                 current_date < new_date.replace(microsecond=0)) or
                    (not current_date and new_date)):
                branch.write({'updated_weblate':
                              new_date.strftime('%Y-%m-%d %H:%M:%S')})
                self.env['runbot.build'].create({'branch_id': branch.id,
                                                 'name': branch.branch_name,
                                                 'uses_weblate': True})

    def _get_branch_quickconnect_url(self, cr, uid, ids, fqdn, dest,
                                     context=None):
        """Remove debug=1 because is too slow
        Remove database default name because is used openerp_test from MQT
        """
        res = super(RunbotBranch, self)._get_branch_quickconnect_url(
            cr, uid, ids, fqdn, dest, context=context)
        for branch in self.browse(cr, uid, ids, context=context):
            if branch.repo_id.is_travis2docker_build:
                dbname = "db=%s-all&" % dest
                res[branch.id] = res[branch.id].replace(dbname, "").replace(
                    "?debug=1", "")
        return res
