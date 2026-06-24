fwbot
#################
This is an implementation for a Gitlab bot that automatically creates forward ports for merge
requests that have been successfully merged on previous versions.

Flow
*****
The bot listens for events through `webhooks <https://docs.gitlab.com/ee/user/project/integrations/webhooks.html>`_ and
sends them to a queue to be processed. As of now, the only events that are handled are those related to merge requests.

The flow for successfully creating a forward port is as follows:

-   A merge request is created. The webhook stores its details for further processing. **Only merge requests with
    protected branch as their target will be processed.**
-   The bot will then prepare the eligible MRs by disabling (if enabled) the option to automatically delete the source
    branch upon merging.
-   Once the bot is notified about the MR being merged, it will mark it for further processing.
-   Upon processing, the bot creates the forward port and deletes the original source branch

Crons
*****
The following cron jobs are continuously run to perform the bot's workload, this ensures
the webhook is fast and responsive, preventing timeouts.

-   Prune Merge Requests: Invalid merge requests are deleted, those that are valid are prepared for a possible forward
    port by the bot.
-   Sync Branches: Repository branches are kept up to date. Stable branches must be known for the bot to decide whether
    a forward port should be performed or not.
-   Create forward ports: The last part of the process. MRs that have been merged have their forward port created. The
    MR's source branch is then deleted.

Forward Port Process
********************
1. Clone target branch
2. Through the Gitlab API cherry-pick commits onto the target branch
3. Create MR
