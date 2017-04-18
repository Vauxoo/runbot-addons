# coding: utf-8
# © 2016 Vauxoo
#   Coded by: dgomez@vauxoo.com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Runbot Log",
    "summary": "Autoreloads runbot logs",
    "version": "9.0",
    "category": "runbot",
    "website": "https://www.vauxoo.com",
    "author": "Vauxoo,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "runbot",
    ],
    "external_dependencies": {
        "python": [
            'travis2docker',
            'docker',
        ],
    },
    "data": [
        "runbot_log.xml",
    ],
    "demo": [
    ],
    "application": False,
    "installable": True,
}
