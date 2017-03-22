def migrate(cr, version):
    """Update database from previous versions, after updating module."""
    cr.execute("""UPDATE runbot_build SET docker_executed_commands = true
               """)
    cr.commit()
