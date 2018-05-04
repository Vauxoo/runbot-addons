# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import subprocess

from odoo import api, models

MAGIC_PID_RUN_NEXT_JOB = -2


class RunbotBuild(models.Model):
    _inherit = "runbot.build"

    @api.depends('name', 'branch_id.name')
    def _get_dest(self):
        builds = self.filtered('branch_id.repo_id.is_docker_image')
        super(RunbotBuild, self - builds)._get_dest()
        for build in builds:
            build.dest = (
                "%05d-%s-%s" % (
                    build.id, build.branch_id.name,
                    build.name.lstrip('sha256:')[:6])
            ).lower()

    def _get_docker_container(self):
        self.ensure_one()
        return "build_%d" % (self.sequence)

    def _checkout(self):
        builds = self.filtered('branch_id.repo_id.is_docker_image')
        return super(RunbotBuild, self - builds)._checkout()

    def _job_10_test_base(self, build, lock_path, log_path):
        if not build.repo_id.is_docker_image:
            return super(RunbotBuild, self)._job_10_test_base(
                build, lock_path, log_path)
        return MAGIC_PID_RUN_NEXT_JOB

    def _job_20_test_all(self, build, lock_path, log_path):
        if not build.branch_id.repo_id.is_docker_image:
            return super(RunbotBuild, self)._job_20_test_all(
                build, lock_path, log_path)
        cmd = [
            'docker', 'run',
            '-p', '%d:%d' % (build.port, 8069),
            '--name=' + build._get_docker_container(),
            '-t', build.branch_id.pull_head_name, '/entrypoint.sh'
        ]
        subprocess.call(['docker', 'rm', '-vf', build._get_docker_container()])
        return self._spawn(cmd, lock_path, log_path, cpu_limit=2100)

    def _job_21_coverage(self, build, lock_path, log_path):
        if not build.repo_id.is_docker_image:
            return super(RunbotBuild, self)._job_21_coverage(
                build, lock_path, log_path)
        return MAGIC_PID_RUN_NEXT_JOB

    def _job_30_run(self, build, lock_path, log_path):
        if not build.repo_id.is_docker_image:
            return super(RunbotBuild, self)._job_30_run(
                build, lock_path, log_path)
        cmd = [
            'docker', 'start', '-i', build._get_docker_container()
        ]
        return self._spawn(cmd, lock_path, log_path, cpu_limit=None)

    def _local_cleanup(self):
        builds = self.filtered('branch_id.repo_id.is_docker_image')
        super(RunbotBuild, self - builds)._local_cleanup()
        for build in builds:
            container_name = build._get_docker_container()
            if container_name:
                subprocess.call(['docker', 'rm', '-vf', container_name])
