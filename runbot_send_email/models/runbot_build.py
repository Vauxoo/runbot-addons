# Copyright <2016> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import re
from urllib.parse import urlparse
from email.utils import formataddr
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class RunbotBuild(models.Model):
    # pylint: disable=method-compute
    _name = "runbot.build"
    _inherit = ['runbot.build', 'mail.thread']

    @api.multi
    def send_email(self):
        template = self.env.ref('runbot_send_email.runbot_send_notif')
        for record in self:
            values = {'email_to': ','.join(self.message_partner_ids.mapped(
                'email'))}
            template.send_mail(record.id, force_send=True, email_values=values)

    def _github_status(self):
        build = super(RunbotBuild, self)._github_status()
        self.filtered(lambda record: record.state == 'running').send_email()
        return build

    def user_follow_unfollow(self):
        """This method remove or add the user from followers of model
        'runbot.build' that has logged.
        """
        if self.env.user.partner_id not in self.message_partner_ids:
            self.message_subscribe_users(user_ids=[self.env.uid])
            return True
        self.message_unsubscribe_users(user_ids=[self.env.uid])
        return False

    @api.model
    def create(self, vals):
        """Add the followers of repository to the followers of build.
        """
        self_ctx = self.with_context(mail_create_nosubscribe=True)
        build_id = super(RunbotBuild, self_ctx).create(vals)
        users = build_id.repo_id.message_partner_ids.mapped('user_ids')
        build_id.message_subscribe_users(user_ids=users.ids)
        self.subscribe_committer()
        return build_id

    def write(self, vals):
        result = super().write(vals)
        self.subscribe_committer()
        return result

    def subscribe_committer(self):
        if not self.committer_email:
            return False
        email = self.committer_email.lstrip('<').rstrip('>')
        partner = self.env['res.partner'].search([
            ('email', '=ilike', email)], limit=1)
        if partner and partner not in self.message_partner_ids:
            self.message_subscribe_users(user_ids=[partner.user_ids.id])
