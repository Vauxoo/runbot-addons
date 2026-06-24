from odoo import fields, models


class RemoteMixin(models.AbstractModel):
    _name = "fwbot.remote.mixin"
    _description = "Remote mixin for fwbot"
    _default_timeout = 10

    last_processed = fields.Datetime(readonly=True)

    @property
    def timeout(self):
        return self.env.context.get("timeout", self._default_timeout)
