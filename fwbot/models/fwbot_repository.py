import logging
import re
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..api import ForwardbotGitlabClient, get_api_data

_logger = logging.getLogger(__name__)


class Repository(models.Model):
    _name = "fwbot.repository"
    _inherit = ["fwbot.remote.mixin"]
    _description = "Git Repository for fwbot"
    _branch_version_regex = re.compile(r"(\d{2}(.\d)?)$")

    name = fields.Char(required=True)
    remote_id = fields.Integer(required=True)
    stable_branches = fields.Char(help="Ordered (lowest to highest), comma separated branches for FW ports")
    overwrite_branches = fields.Boolean(help="Branches won't be updated automatically")
    platform = fields.Selection([("gitlab", "Gitlab")], required=True)
    url = fields.Char(required=True)
    token = fields.Char()

    _sql_constraints = [
        (
            "unique_remote_id",
            "UNIQUE (remote_id)",
            "Two projects can't have the same ID",
        ),
    ]

    @property
    def base_url(self):
        parsed_url = urlparse(self.url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def get_api_data(self):
        self.ensure_one()
        url, token = self.base_url, self.token
        if not url or not token:
            conf_url, conf_token = get_api_data(self.env)
            url = url or conf_url
            token = token or conf_token

        if not url or not token:
            raise ValidationError(_("missing url or access token"))

        return url, token

    @api.model
    def get_branch_version(self, branch_name):
        """Obtain the version from a branch (if available) and return its value.
        Note: main/master are considered the newest version (they have a version value of 1000)
        """
        if branch_name in ["main", "master"]:
            return 1000.0

        version = self._branch_version_regex.search(branch_name)
        if version:
            return float(version[0])

        return -1.0

    def get_next_branch(self, branch_name):
        """Return the branch that follows the current one or an empty string if no branch exists after the
        current one. Only branches that exist in the current repository will be returned.

        For example, if a repository has branches 14.0 and 16.0, the branch that follows 14.0 is 16.0
        If the repo had a 15.0 branch, it would follow after 14.0 instead.
        """
        self.ensure_one()
        if not self.stable_branches:
            return ""
        branches = self.stable_branches.split(",")
        try:
            index = branches.index(branch_name)
            return branches[index + 1]
        except (IndexError, ValidationError):
            return ""

    def update_branches(self, branches):
        branches.sort(key=self.get_branch_version)
        self.stable_branches = ",".join(branches)

    def get_stable_branches(self):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.platform}_get_stable_branches")

        return platform_method()

    def _gitlab_get_stable_branches(self):
        url, token = self.get_api_data()
        response = ForwardbotGitlabClient(url, token, self.timeout).get_protected_branches(self.remote_id)
        response.raise_for_status()

        return [branch["name"] for branch in response.json()]

    def clone_branch(self, source: str, dest: str):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.platform}_clone_branch")

        return platform_method(source, dest)

    def _gitlab_clone_branch(self, source, dest):
        url, token = self.get_api_data()

        return ForwardbotGitlabClient(url, token, self.timeout).create_branch(self.remote_id, dest, source)

    @api.model
    def gitlab_sync_repository_branches(self, auto_commit=False, limit=50, timeout=10):
        repositories = self
        if not repositories:
            repositories: "Repository" = self.search(
                [("overwrite_branches", "=", False), ("platform", "=", "gitlab")],
                limit=limit,
                order="last_processed ASC",
            )

        _logger.info("Will update stable branches for %d repositories", len(repositories))
        if not repositories:
            return

        for repo in repositories:
            try:
                _logger.info("Syncing branches for %s", repo)
                branches = repo.with_context(timeout=timeout).get_stable_branches()
                repo.update_branches(branches)
            except Exception as ex:
                _logger.warning("%s", ex)
                continue
            finally:
                repo.last_processed = fields.Datetime.now()
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit

            _logger.info("Branches for %s updated", repo)
