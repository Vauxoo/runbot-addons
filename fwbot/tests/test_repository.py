from unittest.mock import Mock, patch

from .common import ForwardBotCase, MockResponse


class TestRepository(ForwardBotCase):
    def test_01_get_branch_version(self):
        self.assertEqual(self.model_repo.get_branch_version("main"), 1000.0)
        self.assertEqual(self.model_repo.get_branch_version("master"), 1000.0)

        self.assertEqual(self.model_repo.get_branch_version("12.0"), 12.0)
        self.assertEqual(self.model_repo.get_branch_version("saas-12"), 12.0)

        self.assertEqual(self.model_repo.get_branch_version("16.1"), 16.1)
        self.assertEqual(self.model_repo.get_branch_version("saas-16.1"), 16.1)

        self.assertEqual(self.model_repo.get_branch_version("bazinga"), -1.0)

    def test_02_get_next_branch(self):
        project = self.model_repo.create(
            {
                "name": "rando",
                "url": "hey",
                "remote_id": 5,
                "stable_branches": "12.0,14.0,15.0,master",
                "platform": "gitlab",
            }
        )
        self.assertEqual(project.get_next_branch("12.0"), "14.0")
        self.assertEqual(project.get_next_branch("14.0"), "15.0")
        self.assertEqual(project.get_next_branch("15.0"), "master")
        self.assertFalse(project.get_next_branch("master"))

    def test_03_updated_branches(self):
        project = self.model_repo.create({"name": "timmy", "url": "turner", "remote_id": 4, "platform": "gitlab"})
        project.update_branches(["16.0", "master", "14.0", "12", "saas-12.1", "15.0", "13.0"])

        expected_list = ["12", "saas-12.1", "13.0", "14.0", "15.0", "16.0", "master"]
        self.assertEqual(
            project.stable_branches,
            ",".join(expected_list),
        )

    @patch("odoo.addons.fwbot.models.fwbot_repository.ForwardbotGitlabClient.get")
    def test_04_gitlab_sync_repository_branches(self, mock: Mock):
        mock.side_effect = lambda *_args: MockResponse(
            json_data=[{"name": "15.0"}, {"name": "21.0"}, {"name": "saas-12"}]
        )

        repo = self.model_repo.create(
            {
                "name": "paul",
                "remote_id": 12,
                "platform": "gitlab",
                "url": "https://git.vauxoo.local/paul/repo",
                "token": "letmein",
            }
        )
        repo.gitlab_sync_repository_branches()
        self.assertEqual(repo.stable_branches, "saas-12,15.0,21.0")

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0][0], "https://git.vauxoo.local/api/v4/projects/12/protected_branches")
