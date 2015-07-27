from openerp.osv import osv
from openerp.addons.runbot.runbot import now


class RunbotBuild(osv.osv):
    _inherit = "runbot.build"

    def job_28_wodemo(self, cr, uid, build, lock_path, log_path, args=None):
        build._log('wodemo', 'Start database without demo')
        self.pg_createdb(cr, uid, "%s-wodemo" % build.dest)
        cmd, mods = build.cmd()
        cmd += ['-d', '%s-wodemo' % build.dest,
                '-i', mods, '--stop-after-init',
                '--log-level=info']
        cmd += ['--without-demo=True']
        if "--test-enable" in cmd:
            cmd.remove('--test-enable')
        build.write({'job_start': now()})
        return self.spawn(cmd, lock_path, log_path, cpu_limit=2100)

    def cleanup(self, cr, uid, ids, context=None):
        res = super(RunbotBuild, self).cleanup(
            cr, uid, ids, context=context)
        for build in self.browse(cr, uid, ids, context=context):
            self.pg_dropdb(cr, uid, "%s-wodemo" % build.dest)
        return res
