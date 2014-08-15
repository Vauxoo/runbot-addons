#!/usr/bin/python
# -*- encoding: utf-8 -*-
#
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014 Vauxoo - http://www.vauxoo.com/
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#
#    Coded by: vauxoo consultores (info@vauxoo.com)
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
This module is used to create new fields in the inherited classes.
"""
from openerp.osv import fields, osv
import logging
import os


class RunbotRepo(osv.osv):
    """
    Added pylint_config field to use a configuration of pylint by repository,
    to use for each build of repository.
    """

    _inherit = 'runbot.repo'

    _columns = {
        'pylint_config': fields.many2one('pylint.conf',
                                         string='Pylint Config'),
    }


class RunbotBuild(osv.osv):
    """
    Added pylint_config field, used by default the configuration of repository.
    """

    _inherit = "runbot.build"

    _columns = {
        'pylint_config': fields.many2one('pylint.conf',
                                         string='Pylint Config'),
    }

    def create(self, cr, uid, values, context=None):
        """
        Create a new record for the model.

        The values for the new record are initialized using the ``vals``
        argument, and if necessary the result of ``default_get()``.

        :param cr: database cursor
        :param user: current user id
        :type user: integer
        :param vals: field values for new record, e.g {'field_name': field_value, ...}
        :type vals: dictionary
        :param context: optional context arguments, e.g. {'lang': 'en_us', 'tz': 'UTC', ...}
        :type context: dictionary
        :return: id of new record created
        :raise AccessError: * if user has no create rights on the requested object
                            * if user tries to bypass access rules for create on the requested object
        :raise ValidateError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        **Note**: The type of field values to pass in ``vals`` for relationship fields is specific.
        Please see the description of the :py:meth:`~osv.osv.osv.write` method for details about the possible values and how
        to specify them.

        """
        super(RunbotBuild, self).create(cr, uid, values, context=context)
        branch_id = self.pool.get('runbot.branch').browse(cr, uid,
                                                          values['branch_id'])
        build_id = self.search(cr, uid, [('branch_id', '=',
                                          values['branch_id'])])
        self.write(
            cr, uid, build_id,
             {'pylint_config': branch_id.repo_id and \
             branch_id.repo_id.pylint_config and \
             branch_id.repo_id.pylint_config.id or False}, context=context)

    def job_60_run(self, cr, uid, build, lock_path, log_path, args=None):
        """
        This method is used to run pylint test, getting parameters of the
        pylint configuration, the parameters errors and files to ignore has
        send in list structures to method _run_test_pylint.

        :param build: object build of runbot.
        :param lock_path: path of lock file, this parameter is string.
        :param log_path: path of log file, this parameter is string, where are 
                            has saved the log of test.
        :param args: this parameter not is required, not is used.
        """
        _logger = logging.getLogger("runbot-job")
        if args == None:
            args = {}
        errors = []
        paths_to_test = []
        ignore = []
        result = False
        if build.pylint_config:
            for err in build.pylint_config.error_ids:
                errors.append("-e")
                errors.append(err.code)
            _logger.info("running pylint tests...")
            if build.pylint_config.path_to_test:
                for path_str in build.pylint_config.\
                path_to_test.strip(' ').split(","):
                    if os.path.exists(os.path.join(build.server(), path_str)):
                        paths_to_test.append(
                            os.path.join(build.server(), path_str))
                    else:
                        _logger.info("not exists path [%s]" % (
                            os.path.join(build.server(), path_str), ))
            else:
                if os.path.exists(build.server()):
                    paths_to_test.append(build.server())
                else:
                    _logger.info("not exists path [%s]" % (build.server()))
            if build.pylint_config.ignore:
                ignore.append("--ignore=" + build.pylint_config.ignore)
            result = self.pool.get("pylint.conf")._run_test_pylint(
                cr, uid, errors, paths_to_test, build.server(), ignore,
                log_path, lock_path)
        return result
