# Copyright <2015> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re
import os

import subprocess

from odoo import models, tools

DEFAULT_SSH_PORT = 22


class RunbotBranch(models.Model):
    _inherit = "runbot.branch"

    @tools.ormcache('ssh')
    def _ssh_keyscan(self, ssh):
        """This function execute the command 'ssh-keysan' to avoid the question
        when the command git fetch is excecuted.
        The question is like to:
            'Are you sure you want to continue connecting (yes/no)?'"""
        cmd = ['ssh-keyscan', '-p']
        match = re.search(
            r'(ssh\:\/\/\w+@(?P<host>[a-zA-Z0-9_.-]+))(:{0,1})'
            r'(?P<port>(\d+))?', ssh)
        if not match:
            return False
        data = match.groupdict()
        cmd.append(data['port'] or str(DEFAULT_SSH_PORT))
        cmd.append(data['host'])
        with open(os.path.expanduser('~/.ssh/known_hosts'), 'a+') as hosts:
            new_keys = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
            for key in new_keys.stdout:
                key = key.decode('UTF-8')
                if [line for line in hosts if (line.strip('\n') ==
                                               key.strip('\n'))]:
                    continue
                hosts.write(key + '\n')
        return True

    def _get_branch_quickconnect_url(self, fqdn, dest):
        self.ensure_one()
        res = super(RunbotBranch, self)._get_branch_quickconnect_url(
            fqdn, dest)
        if self.repo_id.is_travis2docker_build:
            dbname = "db=%s-all&" % dest
            res[self.id] = (
                res[self.id].replace(dbname, "").replace("?debug=1", ""))
        return res
