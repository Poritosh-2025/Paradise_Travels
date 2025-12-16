"""
Root package initialization.
Configure PyMySQL as MySQL driver.
"""
from .celery import app as celery_app  # noqa
__all__ = ('celery_app',)
try:
	import pymysql
	pymysql.install_as_MySQLdb()
except ImportError:
	# PyMySQL not installed (using PostgreSQL or sqlite)
	pass
