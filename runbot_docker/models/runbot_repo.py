# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import os
import subprocess
from datetime import datetime

from dateutil import parser

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)


class RunbotRepo(models.Model):
    _inherit = "runbot.repo"

    is_docker_image = fields.Boolean(
        'Use docker image',
        help=('If you select this field, builds will be created with the'
              'specified docker image, which should contain /entrypoint.sh'))

    def docker_pull(self):
        cmd = ['docker', 'pull', self.name, '--all-tags']
        _logger.info("%s", ' '.join(cmd))
        return subprocess.check_output(cmd)

    def get_images_tags(self):
        cmd = [
            'docker', 'images', '-f', 'reference='+self.name,
            '--format', '"{{.Tag}} {{.Digest}} {{.CreatedAt}} {{.ID}}"',
            '--digests'
        ]
        res = subprocess.check_output(cmd)
        res = [i.replace('"', '') for i in res.decode().splitlines()]
        res = [dict(zip(['name', 'sha', 'last', 'image_id'], r.split(' ')))
               for r in res]
        return res

    def set_fetch_head(self, filename):
        """Simulate a change in the file in order to works similar to git"""
        with open(filename, 'w') as fetch_file:
            fetch_file.write(datetime.now().strftime(
                tools.DEFAULT_SERVER_DATETIME_FORMAT))
        return True

    def get_fetch_head(self, filename):
        fetch_time = False
        try:
            fetch_time = open(filename, 'r').read()
        except IOError:
            pass
        if not fetch_time:
            return False
        return datetime.strptime(
            fetch_time, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    def create_build_docker(self):
        """Method create a build for image of docker
        """
        repo = self
        build_obj = self.env['runbot.build']
        branch_obj = self.env['runbot.branch']
        fname_fetch_head = os.path.join(repo.path, 'FETCH_HEAD')
        if not os.path.isdir(repo.path):
            os.makedirs(repo.path)
        fetch_time = self.get_fetch_head(fname_fetch_head)
        if (repo.mode == 'hook' and repo.hook_time and
           repo.hook_time < fetch_time):
            log_msg = ('repo %s skip hook fetch fetch_time: %ss ago'
                       ' hook_time: %ss ago')
            _logger.debug(log_msg, repo.name, fetch_time, repo.hook_time)
            return
        self.docker_pull()
        image_tags = self.get_images_tags()
        self.set_fetch_head(fname_fetch_head)
        for tags in image_tags:
            branch = branch_obj.search([
                ('name', '=', tags['name']), ('repo_id', '=', repo.id)])
            if not branch:
                branch = branch_obj.create(
                    {'repo_id': repo.id, 'name': tags['name']})
            build = build_obj.search([
                ('branch_id', '=', branch.id),
                ('name', '=', tags['sha'])])
            if not build:
                build_value = {
                    'branch_id': branch.id,
                    'name': tags['sha'],
                    'author': self.env.user.name,
                    'author_email': self.env.user.email,
                    'subject': tags['image_id'],
                    'date': parser.parse(
                        tags['last']).strftime("%Y-%m-%d"),
                    }
                build_obj.create(build_value)

    def _update_git(self):
        if not self.is_docker_image:
            return super(RunbotRepo, self)._update_git()
        self.create_build_docker()
