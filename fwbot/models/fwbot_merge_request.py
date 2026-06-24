import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..api import ForwardbotGitlabClient

_logger = logging.getLogger(__name__)
_footer_regex = re.compile(r"This is an automatic forward port for !\d+$")


class MergeRequest(models.Model):
    _name = "fwbot.merge.request"
    _inherit = "fwbot.remote.mixin"
    _description = "Merge Request for fwbot"

    name = fields.Char(help="Merge Request Title", required=True)
    description = fields.Text()
    global_id = fields.Integer(help="ID for this MR on the remote server. Unique across all projects")
    internal_id = fields.Integer(help="Internal ID. Unique inside the target project.")
    source_branch = fields.Char(required=True)
    source_repository_id = fields.Many2one("fwbot.repository", required=True)
    target_branch = fields.Char(required=True)
    target_repository_id = fields.Many2one("fwbot.repository", required=True)
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("opened", "Opened"),
            ("closed", "Closed"),
            ("locked", "Locked"),
            ("merged", "Merged"),
        ],
        default="pending",
        required=True,
    )
    forward_port_id = fields.Many2one("fwbot.merge.request")
    processed = fields.Boolean(default=False)

    _sql_constraints = [
        (
            "unique_global_id",
            "UNIQUE (global_id)",
            "Two MRs can't have the same ID",
        ),
    ]

    def create_forward_port(self):
        self.ensure_one()
        if self.forward_port_id:
            return self.forward_port_id

        forward_branch = self.target_repository_id.get_next_branch(self.target_branch)
        if not forward_branch:
            raise ValidationError(_("can't create forward port, missing forward branch"))

        source_branch = f"{forward_branch}-forward{self.internal_id}-fwb{self.id}"
        name = self.name
        if not self.name.startswith("[FW]"):
            name = f"[FW]{name}" if self.name.startswith("[") else f"[FW] {name}"

        description = self.description
        if _footer_regex.search(description):
            description = _footer_regex.sub(
                f"This is an automatic forward port for !{self.internal_id}",
                description,
            )
        else:
            description += f"\n\n---\nThis is an automatic forward port for !{self.internal_id}"

        self.forward_port_id = self.create(
            {
                "name": name,
                "description": description,
                "source_repository_id": self.source_repository_id.id,
                "source_branch": source_branch,
                "target_repository_id": self.target_repository_id.id,
                "target_branch": forward_branch,
            }
        )

        return self.forward_port_id

    def update_from_object_attributes(self, object_attributes):
        self.ensure_one()
        self.write(
            {
                "name": object_attributes["title"],
                "state": object_attributes["state"],
                "description": object_attributes.get("description"),
                "target_branch": object_attributes["target_branch"],
                "processed": False,
            }
        )

    @api.model
    def gitlab_obtain_from_event(self, data):
        """Obtain (search and create if not found) a record based on the data
        provided by a Merge Request event as described by Gitlab on:
        https://docs.gitlab.com/ee/user/project/integrations/webhook_events.html#merge-request-events

        :return: Tuple consisting of a merge request and a boolean which states whether the merge request
        was created or it already existed (true if it did not exist and was created).
        """
        data_object = data["object_attributes"]

        merge_request = self.search([("global_id", "=", data_object["id"])])
        if merge_request:
            return merge_request, False

        target_repository_id = data_object["target_project_id"]
        target_project = self.env["fwbot.repository"].search([("remote_id", "=", target_repository_id)], limit=1)
        if not target_project:
            target_project = self.env["fwbot.repository"].create(
                {
                    "name": data_object["target"]["path_with_namespace"],
                    "url": data_object["target"]["web_url"],
                    "remote_id": target_repository_id,
                    "platform": "gitlab",
                }
            )

        source_project_id = data_object["source_project_id"]
        source_project = self.env["fwbot.repository"].search([("remote_id", "=", source_project_id)], limit=1)
        if not source_project:
            source_project = self.env["fwbot.repository"].create(
                {
                    "name": data_object["source"]["path_with_namespace"],
                    "url": data_object["source"]["web_url"],
                    "remote_id": source_project_id,
                    "platform": "gitlab",
                }
            )

        return (
            self.env["fwbot.merge.request"].create(
                {
                    "name": data_object["title"],
                    "description": data_object.get("description"),
                    "source_branch": data_object["source_branch"],
                    "source_repository_id": source_project.id,
                    "target_branch": data_object["target_branch"],
                    "target_repository_id": target_project.id,
                    "global_id": data_object["id"],
                    "internal_id": data_object["iid"],
                    "state": data_object["state"],
                }
            ),
            True,
        )

    def update_merge_request(self, payload):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_update_merge_request")

        return platform_method(payload)

    def _gitlab_update_merge_request(self, payload):
        url, token = self.target_repository_id.get_api_data()
        response = ForwardbotGitlabClient(url, token, self.timeout).update_merge_request(
            self.target_repository_id.remote_id, self.internal_id, payload
        )
        response.raise_for_status()

    def push_forward_port(self, forward_port):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_push_forward_port")

        return platform_method(forward_port)

    def _gitlab_push_forward_port(self, forward_port):
        url, token = self.target_repository_id.get_api_data()
        return ForwardbotGitlabClient(url, token, self.timeout).push_forward_port(forward_port)

    def get_merge_commits(self):
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_get_merge_commits")

        return platform_method()

    def _gitlab_get_merge_commits(self):
        url, token = self.target_repository_id.get_api_data()
        response = ForwardbotGitlabClient(url, token, self.timeout).get_merge_commits(
            self.target_repository_id.remote_id, self.internal_id
        )
        response.raise_for_status()

        return response.json()

    def cherry_pick(self, sha: str) -> bool:
        """Apply the given commit (cherry-pick) to the record's source branch"""
        self.ensure_one()
        platform_method = getattr(self, f"_{self.target_repository_id.platform}_cherry_pick")

        return platform_method(sha)

    def _gitlab_cherry_pick(self, sha: str) -> bool:
        url, token = self.target_repository_id.get_api_data()
        response = ForwardbotGitlabClient(url, token, self.timeout).cherry_pick(
            self.target_repository_id.remote_id, sha, self.source_branch
        )

        return response.ok

    @api.model
    def prune_merge_requests(self, limit=50):
        merge_requests = self
        if not merge_requests:
            merge_requests: MergeRequest = self.search(
                [("state", "!=", "merged")], limit=limit, order="last_processed ASC"
            )
        _logger.info("Reviewing %d merge requests for pruning", len(merge_requests))
        if not merge_requests:
            return

        pruned_mrs = self.browse([])
        for merge_request in merge_requests:
            if merge_request.target_branch not in (merge_request.target_repository_id.stable_branches or []):
                pruned_mrs |= merge_request

        _logger.info("Pruning merge requests")
        pruned_mrs.unlink()

    @api.model
    def gitlab_process_pending_for_forward_ports(
        self,
        auto_commit=False,
        limit=50,
        timeout=10,
        states=None,
    ):
        if states is None:
            states = ["merged"]

        pending_for_fw = self.search(
            [
                ("processed", "=", False),
                ("state", "in", states),
                ("target_repository_id.platform", "=", "gitlab"),
            ],
            limit=limit,
            order="id",
        )
        _logger.info("Will process %d MR(s) waiting for a forward port", len(pending_for_fw))
        if not pending_for_fw:
            return

        for merge_request in pending_for_fw:
            try:
                merge_request = merge_request.with_context(timeout=timeout)
                merge_request.create_forward_port()
                forward_port = merge_request.forward_port_id
                _logger.info("Forward port %s created", forward_port)

                # Clone branch used for forward port
                response = merge_request.source_repository_id.clone_branch(
                    forward_port.target_branch,
                    forward_port.source_branch,
                )
                if response.status_code == 400:
                    message = response.json().get("message", "unknown")
                    if message != "Branch already exists":
                        response.raise_for_status()
                else:
                    response.raise_for_status()

                # git cherry-pick
                # empty MR will be created if no cherry-picks are successful
                for commit in reversed(merge_request.get_merge_commits()):
                    _logger.info("cherry-picking %s", commit["id"])
                    if not forward_port.cherry_pick(commit["id"]):
                        _logger.info("cherry-pick failed")
                        break

                # Create merge request (forward port)
                response = merge_request.push_forward_port(merge_request)
                response.raise_for_status()
                data = response.json()
                merge_request.forward_port_id.write(
                    {
                        "global_id": data["id"],
                        "internal_id": data["iid"],
                        "state": data["state"],
                    }
                )
                merge_request.processed = True
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception as ex:
                _logger.error("%s", ex)
                continue

            _logger.info(
                "Forward port %s successfully pushed",
                merge_request.forward_port_id,
            )
