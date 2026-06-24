import random

from odoo.tests.common import TransactionCase


class MockResponse:
    def __init__(self, **kwargs):
        self.json_data = {}
        self.__dict__.update(kwargs)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        pass


class ForwardBotCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.random = random.Random()

    def setUp(self):
        super().setUp()
        self.model_mr = self.env["fwbot.merge.request"]
        self.model_repo = self.env["fwbot.repository"]
        self.env["fwbot.repository"].create(
            {
                "name": "addons/fwbot",
                "url": "https://git.vauxoo.local/addons/fwbot",
                "remote_id": 18,
                "stable_branches": "11.0,12.0,13.0,14.0",
                "platform": "gitlab",
            }
        )

    def _gen_payload(
        self,
        mr_id: int,
        action="open",
        state="opened",
        title="Test MR",
        description="This is a Test MR to see how the Forwardbot works",
        source_project=15,
        source_name="addons/fwbot-dev",
        source_url="https://git.vauxoo.local/addons/fwbot-dev",
        target_project=18,
        target_name="addons/fwbot",
        target_url="https://git.vauxoo.local/addons/fwbot",
        target_branch="11.0",
        event_type="merge_request",
    ):
        return {
            "object_kind": event_type,
            "event_type": event_type,
            "object_attributes": {
                "id": mr_id,
                "iid": mr_id + self.random.randint(1, 100),
                "source_branch": "dev-fwbot",
                "target_branch": target_branch,
                "title": title,
                "state": state,
                "action": action,
                "description": description,
                "source_project_id": source_project,
                "target_project_id": target_project,
                "source": {"path_with_namespace": source_name, "web_url": source_url},
                "target": {"path_with_namespace": target_name, "web_url": target_url},
            },
        }

    def assertMergeRequestEqual(self, data, record):  # pylint: disable=invalid-name
        data = data["object_attributes"]

        self.assertEqual(data["state"], record.state)
        self.assertEqual(data["id"], record.global_id)
        self.assertEqual(data["title"], record.name)
        self.assertEqual(data["source_branch"], record.source_branch)
        self.assertEqual(data["target_branch"], record.target_branch)
        self.assertEqual(data["source_project_id"], record.source_repository_id.remote_id)
        self.assertEqual(data["target_project_id"], record.target_repository_id.remote_id)
