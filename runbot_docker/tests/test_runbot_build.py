# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import subprocess
import time
import xmlrpc.client

from odoo.tests.common import TransactionCase
from odoo.tools.misc import mute_logger

_logger = logging.getLogger(__name__)


class TestRunbotJobs(TransactionCase):

    def setUp(self):
        super(TestRunbotJobs, self).setUp()
        self.build_obj = self.env['runbot.build']
        self.repo_obj = self.env['runbot.repo']
        self.branch_obj = self.env['runbot.branch']
        self.repo = self.repo_obj.search([
            ('is_docker_image', '=', True)], limit=1)
        self.repo_domain = [('repo_id', '=', self.repo.id)]
        self.cron = self.env.ref('runbot.runbot_repo_cron')
        self.cron.write({'active': False})
        self.build_obj.search([]).unlink()
        self.build = None

    @mute_logger('odoo.addons.runbot.models.repo')
    def test_jobs(self):
        'Create build and run all jobs'
        self.assertEqual(len(self.repo), 1, "Repo not found")
        _logger.info("Repo update to get branches")
        self.repo._update(self.repo)
        branch = self.branch_obj.search(self.repo_domain + [
            ('name', '=', 'latest')], limit=1)
        self.assertTrue(branch, "Branch not found")
        self.build = self.build_obj.search([('branch_id', '=', branch.id)])
        _logger.info("Downloading docker image...")
        subprocess.call(['docker', 'pull', self.repo.name])
        _logger.info("...Docker image downloaded")
        _logger.info("Repo Cron to change state to pending -> testing")
        self.assertEqual(
            self.build.state, u'pending', "State should be pending")
        self.repo._cron()
        self.assertEqual(
            self.build.state, u'testing', "State should be testing")
        self.assertEqual(
            self.build.job, u'job_20_test_all',
            "Job should be job_20_test_all")
        new_current_job = self.wait_change_job(
            'job_20_test_all', self.build)
        self.assertEqual(
            new_current_job, u'job_30_run',
            "Job should be job_30_run")
        self.assertEqual(
            self.build.state, u'running',
            "Job state should be running")
        self.repo._cron()
        self.assertEqual(
            self.build.state, u'running',
            "Job state should be running still")
        user_ids = self.connection_test(self.build, 36, 10)
        self.assertTrue(
            len(user_ids) >= 1, "Failed connection test")
        self.build._kill()
        self.assertEqual(
            self.build.state, u'done', "Job state should be done")

    def connection_test(self, build, attempts=1, delay=0):
        username = "admin"
        password = "admin"
        database_name = "openerp_test"
        port = build.port
        host = '127.0.0.1'
        user_ids = []
        for _ in range(attempts):
            try:
                sock_common = xmlrpc.client.ServerProxy(
                    "http://%s:%d/xmlrpc/common" % (host, port))
                uid = sock_common.login(
                    database_name, username, password)
                sock = xmlrpc.client.ServerProxy(
                    "http://%s:%d/xmlrpc/object" % (host, port))
                user_ids = sock.execute(
                    database_name, uid, password, 'res.users',
                    'search', [('login', '=', 'admin')])
                _logger.info("Trying connect... connected.")
                return user_ids
            except BaseException:
                _logger.info("Trying connect to build %s %s:%s... failed.",
                             build.sequence, host, port)
            time.sleep(delay)
        return user_ids

    def wait_change_job(self, current_job, build,
                        loops=60, timeout=15):
        for loop in range(loops):
            _logger.info("Repo Cron to wait change of state")
            self.repo._cron()
            if build.job != current_job:
                break
            time.sleep(timeout)
        return build.job
