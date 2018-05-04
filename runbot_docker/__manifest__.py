# Copyright <2018> <Vauxoo info@vauxoo.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Runbot to docker",
    "summary": "Generate docker with odoo instance based on docker images",
    "version": "11.0.1.0.0",
    "category": "runbot",
    "website": "https://odoo-community.org/",
    "author": "Vauxoo,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        'runbot'
    ],
    "data": [
        'views/runbot_repo_view.xml',
        'templates/frontend.xml',
    ],
    "demo": [
        'demo/runbot_repo_demo.xml',
    ],
    "application": False,
    "installable": True,
}
